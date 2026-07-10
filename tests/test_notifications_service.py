from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.notifications.fcm import FcmPushError, FirebaseCloudMessagingClient
from app.modules.notifications.service import NotificationService
from app.modules.notifications.schemas import FcmTokenCreate


class _FakeRepo:
    def __init__(self) -> None:
        self.tokens = [SimpleNamespace(token="fcm-token-1")]
        self.deactivated: list[str] = []
        self.upsert_args = None

    async def upsert_fcm_token(self, *, user_id: int, token: str, platform: str | None, user_agent: str | None):
        self.upsert_args = {
            "user_id": user_id,
            "token": token,
            "platform": platform,
            "user_agent": user_agent,
        }
        return SimpleNamespace(id=9, token=token, platform=platform, is_active=True)

    async def count_active_fcm_tokens_for_user(self, user_id: int) -> int:
        return len(self.tokens)

    async def list_active_fcm_tokens_for_user(self, user_id: int):
        return self.tokens

    async def deactivate_fcm_token(self, token: str) -> bool:
        self.deactivated.append(token)
        return True


@pytest.mark.asyncio
async def test_register_fcm_token_commits_and_returns_record():
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    service = NotificationService(session)  # type: ignore[arg-type]
    service.repo = _FakeRepo()

    record = await service.register_fcm_token(
        user_id=7,
        payload=FcmTokenCreate(token="abc-token", platform="android"),
        user_agent="Flutter/1.0",
    )

    assert record.token == "abc-token"
    assert service.repo.upsert_args == {
        "user_id": 7,
        "token": "abc-token",
        "platform": "android",
        "user_agent": "Flutter/1.0",
    }
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_fcm_to_user_delivers_payload_and_clears_invalid_tokens(monkeypatch):
    session = SimpleNamespace(commit=AsyncMock())
    service = NotificationService(session)  # type: ignore[arg-type]
    repo = _FakeRepo()
    service.repo = repo

    sent: list[tuple[str, dict]] = []

    monkeypatch.setattr(FirebaseCloudMessagingClient, "is_configured", staticmethod(lambda: True))

    def _send_to_token(*, token: str, payload: dict):
        sent.append((token, payload))
        raise FcmPushError("token is stale", status_code=404, error_code="UNREGISTERED", token_invalid=True)

    monkeypatch.setattr(FirebaseCloudMessagingClient, "send_to_token", staticmethod(_send_to_token))

    await service.send_fcm_to_user(
        user_id=7,
        payload={
            "title": "Order placed",
            "body": "Restaurant received your order.",
            "deep_link": "/orders",
            "order_id": 55,
        },
    )

    assert sent == [
        (
            "fcm-token-1",
            {
                "title": "Order placed",
                "body": "Restaurant received your order.",
                "deep_link": "/orders",
                "order_id": 55,
            },
        )
    ]
    assert repo.deactivated == ["fcm-token-1"]
    session.commit.assert_awaited_once()
