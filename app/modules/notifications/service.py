from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import HTTPException, status
from pywebpush import WebPushException, webpush
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.notifications.fcm import FirebaseCloudMessagingClient, FcmPushError
from app.modules.notifications.models import UserNotification
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import FcmTokenCreate, WebPushSubscriptionCreate

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)

    def get_public_vapid_key(self) -> str:
        if not settings.web_push_vapid_public_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Web push is not configured.",
            )
        return settings.web_push_vapid_public_key

    async def register_web_push_subscription(
        self,
        *,
        user_id: int,
        payload: WebPushSubscriptionCreate,
        user_agent: str | None,
    ):
        record = await self.repo.upsert_web_push_subscription(
            user_id=user_id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
            user_agent=user_agent,
        )
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def unregister_web_push_subscription(self, endpoint: str) -> bool:
        removed = await self.repo.deactivate_subscription(endpoint)
        await self.session.commit()
        return removed

    async def get_web_push_status(self, user_id: int) -> dict[str, Any]:
        active_subscription_count = await self.repo.count_active_subscriptions_for_user(user_id)
        return {
            "has_subscription": active_subscription_count > 0,
            "active_subscription_count": active_subscription_count,
        }

    async def register_fcm_token(
        self,
        *,
        user_id: int,
        payload: FcmTokenCreate,
        user_agent: str | None,
    ):
        record = await self.repo.upsert_fcm_token(
            user_id=user_id,
            token=payload.token,
            platform=payload.platform,
            user_agent=user_agent,
        )
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_fcm_status(self, user_id: int) -> dict[str, Any]:
        active_token_count = await self.repo.count_active_fcm_tokens_for_user(user_id)
        return {
            "has_token": active_token_count > 0,
            "active_token_count": active_token_count,
        }

    async def create_notification_from_payload(
        self,
        *,
        recipient_user_id: int,
        payload: dict[str, Any],
        restaurant_id: int | None = None,
        order_id: int | None = None,
        message_id: int | None = None,
        actor_user_id: int | None = None,
    ) -> UserNotification:
        event_key = str(payload.get("event_id") or payload.get("event") or f"notification-{recipient_user_id}")
        audience = str(payload.get("audience") or "user")
        category = str(payload.get("category") or payload.get("event") or "general")

        record = await self.repo.upsert_user_notification(
            recipient_user_id=recipient_user_id,
            audience=audience,
            category=category,
            event_key=event_key,
            title=str(payload.get("title") or "Notification"),
            body=str(payload.get("body") or ""),
            deep_link=payload.get("deep_link"),
            payload_json=payload,
            restaurant_id=restaurant_id if restaurant_id is not None else payload.get("restaurant_id"),
            order_id=order_id if order_id is not None else payload.get("order_id"),
            message_id=message_id if message_id is not None else payload.get("message_id"),
            actor_user_id=actor_user_id if actor_user_id is not None else payload.get("actor_user_id"),
        )
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def create_notifications_for_users(
        self,
        *,
        recipient_user_ids: list[int],
        payload: dict[str, Any],
        restaurant_id: int | None = None,
        order_id: int | None = None,
        message_id: int | None = None,
        actor_user_id: int | None = None,
    ) -> list[UserNotification]:
        seen: set[int] = set()
        records: list[UserNotification] = []
        for recipient_user_id in recipient_user_ids:
            if recipient_user_id in seen:
                continue
            seen.add(recipient_user_id)
            record = await self.repo.upsert_user_notification(
                recipient_user_id=recipient_user_id,
                audience=str(payload.get("audience") or "user"),
                category=str(payload.get("category") or payload.get("event") or "general"),
                event_key=str(payload.get("event_id") or payload.get("event") or f"notification-{recipient_user_id}"),
                title=str(payload.get("title") or "Notification"),
                body=str(payload.get("body") or ""),
                deep_link=payload.get("deep_link"),
                payload_json=payload,
                restaurant_id=restaurant_id if restaurant_id is not None else payload.get("restaurant_id"),
                order_id=order_id if order_id is not None else payload.get("order_id"),
                message_id=message_id if message_id is not None else payload.get("message_id"),
                actor_user_id=actor_user_id if actor_user_id is not None else payload.get("actor_user_id"),
            )
            records.append(record)
        await self.session.commit()
        for record in records:
            await self.session.refresh(record)
        return records

    async def create_merchant_notifications_from_payload(
        self,
        *,
        restaurant_id: int,
        payload: dict[str, Any],
        actor_user_id: int | None = None,
        order_id: int | None = None,
        message_id: int | None = None,
    ) -> list[UserNotification]:
        merchant_user_ids = await self.repo.list_merchant_user_ids_for_restaurant(restaurant_id)
        return await self.create_notifications_for_users(
            recipient_user_ids=merchant_user_ids,
            payload=payload,
            restaurant_id=restaurant_id,
            order_id=order_id,
            message_id=message_id,
            actor_user_id=actor_user_id,
        )

    async def list_notifications(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
        unread_only: bool = False,
        include_dismissed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UserNotification]:
        return await self.repo.list_user_notifications(
            recipient_user_id=recipient_user_id,
            audience=audience,
            restaurant_id=restaurant_id,
            unread_only=unread_only,
            include_dismissed=include_dismissed,
            limit=limit,
            offset=offset,
        )

    async def count_notifications(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
        unread_only: bool = False,
        include_dismissed: bool = False,
    ) -> int:
        return await self.repo.count_user_notifications(
            recipient_user_id=recipient_user_id,
            audience=audience,
            restaurant_id=restaurant_id,
            unread_only=unread_only,
            include_dismissed=include_dismissed,
        )

    async def mark_notification_read(self, *, recipient_user_id: int, notification_id: int) -> UserNotification | None:
        record = await self.repo.mark_user_notification_read(
            recipient_user_id=recipient_user_id,
            notification_id=notification_id,
        )
        if record is not None:
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def mark_all_notifications_read(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
    ) -> int:
        updated = await self.repo.mark_all_user_notifications_read(
            recipient_user_id=recipient_user_id,
            audience=audience,
            restaurant_id=restaurant_id,
        )
        await self.session.commit()
        return updated

    async def dismiss_notification(self, *, recipient_user_id: int, notification_id: int) -> UserNotification | None:
        record = await self.repo.dismiss_user_notification(
            recipient_user_id=recipient_user_id,
            notification_id=notification_id,
        )
        if record is not None:
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def send_web_push_to_user(self, *, user_id: int, payload: dict[str, Any]) -> None:
        if not self._is_web_push_configured():
            return

        subscriptions = await self.repo.list_active_subscriptions_for_user(user_id)
        if not subscriptions:
            return

        for subscription in subscriptions:
            await self._deliver_subscription(subscription.endpoint, subscription.p256dh, subscription.auth, payload)

    async def send_web_push_to_merchants(self, *, restaurant_id: int, payload: dict[str, Any]) -> None:
        if not self._is_web_push_configured():
            return

        merchant_user_ids = await self.repo.list_merchant_user_ids_for_restaurant(restaurant_id)
        if not merchant_user_ids:
            logger.warning('Web push: no merchant users found for restaurant %s', restaurant_id)
            return
        for user_id in merchant_user_ids:
            subscriptions = await self.repo.list_active_subscriptions_for_user(user_id)
            if not subscriptions:
                logger.warning('Web push: merchant user %s has no active subscriptions', user_id)
                continue
            for subscription in subscriptions:
                await self._deliver_subscription(subscription.endpoint, subscription.p256dh, subscription.auth, payload)

    async def send_fcm_to_user(self, *, user_id: int, payload: dict[str, Any]) -> None:
        if not FirebaseCloudMessagingClient.is_configured():
            logger.warning("FCM not configured, skipping push delivery.")
            return

        tokens = await self.repo.list_active_fcm_tokens_for_user(user_id)
        if not tokens:
            return

        for record in tokens:
            try:
                await asyncio.to_thread(
                    FirebaseCloudMessagingClient.send_to_token,
                    token=record.token,
                    payload=payload,
                )
            except FcmPushError as exc:
                logger.warning(
                    "fcm push failed token=%s status=%s error=%s",
                    record.token,
                    exc.status_code,
                    exc.error_code,
                )
                if exc.token_invalid:
                    await self.repo.deactivate_fcm_token(record.token)
                    await self.session.commit()
            except Exception as exc:
                logger.exception("unexpected fcm push failure token=%s error=%s", record.token, exc)

    async def send_fcm_to_merchants(self, *, restaurant_id: int, payload: dict[str, Any]) -> None:
        if not FirebaseCloudMessagingClient.is_configured():
            logger.warning("FCM not configured, skipping merchant push delivery.")
            return

        merchant_user_ids = await self.repo.list_merchant_user_ids_for_restaurant(restaurant_id)
        if not merchant_user_ids:
            logger.warning("FCM: no merchant users found for restaurant %s", restaurant_id)
            return

        for user_id in merchant_user_ids:
            await self.send_fcm_to_user(user_id=user_id, payload=payload)

    async def _deliver_subscription(
        self,
        endpoint: str,
        p256dh: str,
        auth: str,
        payload: dict[str, Any],
    ) -> None:
        subscription_info = {
            "endpoint": endpoint,
            "keys": {
                "p256dh": p256dh,
                "auth": auth,
            },
        }

        try:
            await asyncio.to_thread(
                webpush,
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=settings.web_push_vapid_private_key,
                vapid_claims={"sub": settings.web_push_subject},
            )
        except WebPushException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logger.warning("web push failed endpoint=%s status=%s error=%s", endpoint, status_code, exc)
            error_text = str(exc)
            if status_code in {404, 410} or "VAPID credentials" in error_text:
                await self.repo.deactivate_subscription(endpoint)
                await self.session.commit()
        except Exception as exc:
            logger.exception("unexpected web push failure endpoint=%s error=%s", endpoint, exc)

    @staticmethod
    def build_order_notification_payload(
        *,
        audience: str,
        event: str,
        order_id: int,
        order_number: str,
        status: str,
        restaurant_id: int | None,
        restaurant_name: str,
        title: str,
        body: str,
        deep_link: str,
    ) -> dict[str, Any]:
        return {
            "category": "order",
            "event": event,
            "event_id": f"order-{order_id}-{status}-{audience}",
            "audience": audience,
            "order_id": order_id,
            "order_number": order_number,
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant_name,
            "status": status,
            "title": title,
            "body": body,
            "deep_link": deep_link,
            "tag": f"order-{order_id}-{status}",
        }

    @staticmethod
    def build_message_notification_payload(
        *,
        audience: str,
        message_id: int,
        restaurant_id: int,
        restaurant_name: str,
        customer_id: int,
        customer_name: str,
        sender_name: str,
        is_from_merchant: bool,
        title: str,
        body: str,
        deep_link: str,
    ) -> dict[str, Any]:
        return {
            "category": "message",
            "event": "new_message",
            "event_id": f"message-{message_id}-{audience}",
            "audience": audience,
            "message_id": message_id,
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant_name,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "sender_name": sender_name,
            "is_from_merchant": is_from_merchant,
            "title": title,
            "body": body,
            "deep_link": deep_link,
            "tag": f"message-{message_id}-{audience}",
        }

    @staticmethod
    def _is_web_push_configured() -> bool:
        missing = []
        if not settings.web_push_vapid_public_key:
            missing.append('web_push_vapid_public_key')
        if not settings.web_push_vapid_private_key:
            missing.append('web_push_vapid_private_key')
        if not settings.web_push_subject:
            missing.append('web_push_subject')
        if missing:
            logger.warning('Web push not configured, missing: %s', ', '.join(missing))
        return bool(
            settings.web_push_vapid_public_key
            and settings.web_push_vapid_private_key
            and settings.web_push_subject
        )
