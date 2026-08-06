from unittest.mock import AsyncMock, patch

import pytest

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.notifications.fcm import FcmPushError
from app.modules.notifications.service import NotificationService, PushDeliveryPartialFailure


class _FakeSession:
    async def commit(self):
        pass


class _FakeToken:
    def __init__(self, token: str):
        self.token = token


def _service_with_repo(**repo_overrides):
    service = NotificationService.__new__(NotificationService)
    service.session = _FakeSession()
    repo = AsyncMock()
    for name, value in repo_overrides.items():
        setattr(repo, name, value)
    service.repo = repo
    return service, repo


@pytest.mark.asyncio
async def test_fcm_transient_failure_records_outbox_row_and_raises():
    service, repo = _service_with_repo(
        list_active_fcm_tokens_for_user=AsyncMock(return_value=[_FakeToken("tok-1")]),
    )

    with patch(
        "app.modules.notifications.service.FirebaseCloudMessagingClient.is_configured", return_value=True
    ), patch(
        "app.modules.notifications.service.FirebaseCloudMessagingClient.send_to_token",
        side_effect=FcmPushError("rate limited", status_code=429, token_invalid=False),
    ):
        with pytest.raises(PushDeliveryPartialFailure):
            await service.send_fcm_to_user(user_id=1, payload={"event": "order_update"})

    repo.record_push_delivery_failure.assert_awaited_once()
    repo.deactivate_fcm_token.assert_not_called()


@pytest.mark.asyncio
async def test_fcm_invalid_token_deactivates_without_recording_failure():
    service, repo = _service_with_repo(
        list_active_fcm_tokens_for_user=AsyncMock(return_value=[_FakeToken("tok-1")]),
    )

    with patch(
        "app.modules.notifications.service.FirebaseCloudMessagingClient.is_configured", return_value=True
    ), patch(
        "app.modules.notifications.service.FirebaseCloudMessagingClient.send_to_token",
        side_effect=FcmPushError("unregistered", status_code=404, token_invalid=True),
    ):
        # An invalid token is a permanent, non-retryable condition — it should
        # not raise, just deactivate the token.
        await service.send_fcm_to_user(user_id=1, payload={"event": "order_update"})

    repo.deactivate_fcm_token.assert_awaited_once_with("tok-1")
    repo.record_push_delivery_failure.assert_not_called()


@pytest.mark.asyncio
async def test_fcm_success_clears_any_previous_outbox_row():
    service, repo = _service_with_repo(
        list_active_fcm_tokens_for_user=AsyncMock(return_value=[_FakeToken("tok-1")]),
    )

    with patch(
        "app.modules.notifications.service.FirebaseCloudMessagingClient.is_configured", return_value=True
    ), patch(
        "app.modules.notifications.service.FirebaseCloudMessagingClient.send_to_token",
        return_value=None,
    ):
        await service.send_fcm_to_user(user_id=1, payload={"event": "order_update"})

    repo.clear_push_delivery_failure.assert_awaited_once()
    repo.record_push_delivery_failure.assert_not_called()
