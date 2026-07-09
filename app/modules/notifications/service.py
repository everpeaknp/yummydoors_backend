from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import HTTPException, status
from pywebpush import WebPushException, webpush
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import WebPushSubscriptionCreate

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
            return

        for user_id in merchant_user_ids:
            await self.send_web_push_to_user(user_id=user_id, payload=payload)

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
            if status_code in {404, 410}:
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
    def _is_web_push_configured() -> bool:
        return bool(
            settings.web_push_vapid_public_key
            and settings.web_push_vapid_private_key
            and settings.web_push_subject
        )
