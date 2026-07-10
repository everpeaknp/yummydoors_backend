from __future__ import annotations

import base64
import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from app.core.config import settings

logger = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
FCM_ANDROID_CHANNEL_ID = "yummydoors_high_importance"


class FcmPushError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        token_invalid: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.token_invalid = token_invalid


@lru_cache(maxsize=1)
def _load_credentials_bundle() -> tuple[service_account.Credentials, str]:
    raw_base64 = (
        settings.firebase_credentials_base64
        or os.getenv("FIREBASE_CREDENTIALS_BASE64")
        or ""
    ).strip()
    info: dict[str, Any] | None = None

    if raw_base64:
        try:
            info = json.loads(base64.b64decode(raw_base64).decode("utf-8"))
        except Exception as exc:
            raise FcmPushError("Firebase credential base64 is invalid.") from exc
    else:
        credentials_path = (
            settings.firebase_credentials_path
            or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            or ""
        ).strip()
        if credentials_path:
            path = Path(credentials_path)
            if not path.exists():
                raise FcmPushError(
                    f"Firebase credential file not found: {path}",
                )
            try:
                info = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise FcmPushError("Firebase credential file is invalid JSON.") from exc

    if not info:
        raise FcmPushError("Firebase credentials are not configured.")

    project_id = settings.firebase_project_id or info.get("project_id")
    if not project_id:
        raise FcmPushError("Firebase project_id is missing from credentials.")

    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=[FCM_SCOPE],
    )
    return credentials, project_id


class FirebaseCloudMessagingClient:
    @classmethod
    def is_configured(cls) -> bool:
        try:
            _load_credentials_bundle()
            return True
        except FcmPushError:
            return False

    @classmethod
    def send_to_token(cls, *, token: str, payload: dict[str, Any]) -> None:
        credentials, project_id = _load_credentials_bundle()
        credentials.refresh(GoogleAuthRequest())

        response = requests.post(
            FCM_ENDPOINT.format(project_id=project_id),
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json",
            },
            json={"message": cls._build_message(token=token, payload=payload)},
            timeout=10,
        )

        if response.ok:
            return

        raise cls._build_error(response)

    @staticmethod
    def _build_message(token: str, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title") or "YummyDoors update")
        body = str(payload.get("body") or "")
        data = {
            key: "" if value is None else str(value)
            for key, value in payload.items()
        }

        return {
            "token": token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": data,
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": FCM_ANDROID_CHANNEL_ID,
                    "sound": "default",
                },
            },
            "apns": {
                "payload": {
                    "aps": {
                        "sound": "default",
                    }
                }
            },
        }

    @staticmethod
    def _build_error(response: requests.Response) -> FcmPushError:
        status_code = response.status_code
        error_code: str | None = None
        message = response.text.strip() or "FCM delivery failed."

        try:
            payload = response.json()
        except Exception:
            payload = None

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = str(error.get("message") or message)
                error_code = error.get("status") or error_code
                details = error.get("details")
                if isinstance(details, list):
                    for item in details:
                        if not isinstance(item, dict):
                            continue
                        detail_type = str(item.get("@type") or "")
                        if "FcmError" in detail_type and item.get("errorCode"):
                            error_code = str(item["errorCode"])
                            break

        token_invalid = status_code in {400, 404} and (
            error_code in {"NOT_FOUND", "UNREGISTERED", "INVALID_ARGUMENT"}
            or "registration token" in message.lower()
            or "requested entity was not found" in message.lower()
        )
        return FcmPushError(
            message,
            status_code=status_code,
            error_code=error_code,
            token_invalid=token_invalid,
        )
