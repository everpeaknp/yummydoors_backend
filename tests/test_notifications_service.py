from datetime import UTC, datetime
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
        self.notifications: list[SimpleNamespace] = []
        self.merchant_user_ids = [31, 32]

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

    async def upsert_user_notification(
        self,
        *,
        recipient_user_id: int,
        audience: str,
        category: str,
        event_key: str,
        title: str,
        body: str,
        deep_link: str | None,
        payload_json: dict | None,
        restaurant_id: int | None = None,
        order_id: int | None = None,
        message_id: int | None = None,
        actor_user_id: int | None = None,
    ):
        record = SimpleNamespace(
            id=len(self.notifications) + 1,
            recipient_user_id=recipient_user_id,
            audience=audience,
            category=category,
            event_key=event_key,
            title=title,
            body=body,
            deep_link=deep_link,
            payload_json=payload_json,
            restaurant_id=restaurant_id,
            order_id=order_id,
            message_id=message_id,
            actor_user_id=actor_user_id,
            read_at=None,
            dismissed_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.notifications.append(record)
        return record

    async def list_merchant_user_ids_for_restaurant(self, restaurant_id: int) -> list[int]:
        return list(self.merchant_user_ids)

    async def list_user_notifications(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
        unread_only: bool = False,
        include_dismissed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ):
        items = [
            notification
            for notification in self.notifications
            if notification.recipient_user_id == recipient_user_id
            and (audience is None or notification.audience == audience)
            and (restaurant_id is None or notification.restaurant_id == restaurant_id)
            and (not unread_only or notification.read_at is None)
            and (include_dismissed or notification.dismissed_at is None)
        ]
        return items[offset : offset + limit]

    async def count_user_notifications(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
        unread_only: bool = False,
        include_dismissed: bool = False,
    ) -> int:
        return len(
            await self.list_user_notifications(
                recipient_user_id=recipient_user_id,
                audience=audience,
                restaurant_id=restaurant_id,
                unread_only=unread_only,
                include_dismissed=include_dismissed,
                limit=10_000,
                offset=0,
            )
        )

    async def mark_user_notification_read(self, *, recipient_user_id: int, notification_id: int):
        for notification in self.notifications:
            if notification.id == notification_id and notification.recipient_user_id == recipient_user_id:
                notification.read_at = datetime.now(UTC)
                return notification
        return None

    async def mark_all_user_notifications_read(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
    ) -> int:
        count = 0
        for notification in self.notifications:
            if notification.recipient_user_id != recipient_user_id:
                continue
            if audience is not None and notification.audience != audience:
                continue
            if restaurant_id is not None and notification.restaurant_id != restaurant_id:
                continue
            if notification.read_at is None:
                notification.read_at = datetime.now(UTC)
                count += 1
        return count

    async def dismiss_user_notification(self, *, recipient_user_id: int, notification_id: int):
        for notification in self.notifications:
            if notification.id == notification_id and notification.recipient_user_id == recipient_user_id:
                notification.dismissed_at = datetime.now(UTC)
                return notification
        return None


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


def test_build_message_notification_payload_includes_deep_link_and_tag():
    payload = NotificationService.build_message_notification_payload(
        audience="customer",
        message_id=91,
        restaurant_id=12,
        restaurant_name="Subash Restro",
        customer_id=44,
        customer_name="Riya",
        sender_name="Subash Restro",
        is_from_merchant=True,
        title="New message from Subash Restro",
        body="Your order is ready.",
        deep_link="/messages?restaurant_id=12&restaurant_name=Subash+Restro",
    )

    assert payload["event"] == "new_message"
    assert payload["event_id"] == "message-91-customer"
    assert payload["deep_link"] == "/messages?restaurant_id=12&restaurant_name=Subash+Restro"
    assert payload["tag"] == "message-91-customer"
    assert payload["is_from_merchant"] is True


@pytest.mark.asyncio
async def test_send_fcm_to_merchants_sends_to_each_merchant_user(monkeypatch):
    session = SimpleNamespace(commit=AsyncMock())
    service = NotificationService(session)  # type: ignore[arg-type]
    repo = _FakeRepo()
    repo.tokens = [SimpleNamespace(token="merchant-token")]
    repo.merchant_user_ids = [11, 12]

    async def list_merchant_user_ids_for_restaurant(restaurant_id: int):
        return repo.merchant_user_ids

    repo.list_merchant_user_ids_for_restaurant = list_merchant_user_ids_for_restaurant  # type: ignore[assignment]
    service.repo = repo

    sent: list[tuple[int, dict]] = []

    monkeypatch.setattr(FirebaseCloudMessagingClient, "is_configured", staticmethod(lambda: True))

    async def fake_send_fcm_to_user(*, user_id: int, payload: dict):
        sent.append((user_id, payload))

    monkeypatch.setattr(service, "send_fcm_to_user", fake_send_fcm_to_user)

    await service.send_fcm_to_merchants(
        restaurant_id=99,
        payload={
            "title": "New message",
            "body": "Someone messaged you.",
            "deep_link": "/merchant/messages?customer_id=7",
        },
    )

    assert sent == [
        (
            11,
            {
                "title": "New message",
                "body": "Someone messaged you.",
                "deep_link": "/merchant/messages?customer_id=7",
            },
        ),
        (
            12,
            {
                "title": "New message",
                "body": "Someone messaged you.",
                "deep_link": "/merchant/messages?customer_id=7",
            },
        ),
    ]


@pytest.mark.asyncio
async def test_create_notification_from_payload_persists_row_and_commits():
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    service = NotificationService(session)  # type: ignore[arg-type]
    repo = _FakeRepo()
    service.repo = repo

    payload = {
        "category": "order",
        "event": "order_update",
        "event_id": "order-55-delivered-customer",
        "audience": "customer",
        "title": "Order delivered",
        "body": "Your order arrived.",
        "deep_link": "/orders",
        "order_id": 55,
    }

    record = await service.create_notification_from_payload(
        recipient_user_id=7,
        payload=payload,
        restaurant_id=12,
        actor_user_id=3,
    )

    assert record.recipient_user_id == 7
    assert record.category == "order"
    assert record.order_id == 55
    assert len(repo.notifications) == 1
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_merchant_notifications_from_payload_fans_out_to_all_merchant_users():
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    service = NotificationService(session)  # type: ignore[arg-type]
    repo = _FakeRepo()
    repo.merchant_user_ids = [11, 12]
    service.repo = repo

    payload = {
        "category": "message",
        "event": "new_message",
        "event_id": "message-91-merchant",
        "audience": "merchant",
        "title": "New message",
        "body": "A customer sent a message.",
        "deep_link": "/merchant/messages?customer_id=7",
    }

    records = await service.create_merchant_notifications_from_payload(
        restaurant_id=99,
        payload=payload,
        actor_user_id=7,
        message_id=91,
    )

    assert [record.recipient_user_id for record in records] == [11, 12]
    assert [record.restaurant_id for record in records] == [99, 99]
    assert len(repo.notifications) == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_notification_read_and_dismiss_updates_notification_rows():
    session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
    service = NotificationService(session)  # type: ignore[arg-type]
    repo = _FakeRepo()
    repo.notifications = [
        SimpleNamespace(
            id=1,
            recipient_user_id=7,
            audience="customer",
            category="order",
            event_key="order-1",
            title="Order placed",
            body="Order received.",
            deep_link="/orders",
            payload_json={},
            restaurant_id=None,
            order_id=1,
            message_id=None,
            actor_user_id=None,
            read_at=None,
            dismissed_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    ]
    service.repo = repo

    record = await service.mark_notification_read(recipient_user_id=7, notification_id=1)
    assert record is not None
    assert record.read_at is not None

    dismissed = await service.dismiss_notification(recipient_user_id=7, notification_id=1)
    assert dismissed is not None
    assert dismissed.dismissed_at is not None
