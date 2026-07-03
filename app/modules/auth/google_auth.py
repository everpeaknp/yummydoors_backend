from __future__ import annotations

import asyncio

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings


async def verify_google_credential(credential: str) -> dict:
    return await asyncio.to_thread(_verify_google_credential_sync, credential)


def _verify_google_credential_sync(credential: str) -> dict:
    if not settings.google_client_id:
        raise ValueError("Google client ID is not configured.")

    payload = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        settings.google_client_id,
    )
    return dict(payload)
