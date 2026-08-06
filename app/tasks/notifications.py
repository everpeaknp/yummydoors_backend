from __future__ import annotations

import asyncio
from typing import Any

from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.modules.auth.notifications import send_email_message, send_password_reset_code
from app.modules.notifications.service import NotificationService, PushDeliveryPartialFailure


async def _send_user_notification_async(user_id: int, payload: dict[str, Any]) -> None:
    async with AsyncSessionLocal() as session:
        service = NotificationService(session)
        errors: list[str] = []
        for channel_call in (service.send_web_push_to_user, service.send_fcm_to_user):
            try:
                await channel_call(user_id=user_id, payload=payload)
            except PushDeliveryPartialFailure as exc:
                errors.append(str(exc))
        if errors:
            raise PushDeliveryPartialFailure("; ".join(errors))


async def _send_merchant_notification_async(restaurant_id: int, payload: dict[str, Any]) -> None:
    async with AsyncSessionLocal() as session:
        service = NotificationService(session)
        errors: list[str] = []
        for channel_call in (service.send_web_push_to_merchants, service.send_fcm_to_merchants):
            try:
                await channel_call(restaurant_id=restaurant_id, payload=payload)
            except PushDeliveryPartialFailure as exc:
                errors.append(str(exc))
        if errors:
            raise PushDeliveryPartialFailure("; ".join(errors))


@celery_app.task(name="yummydoors.notifications.send_password_reset_email", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_password_reset_email_task(self, recipient: str, code: str) -> dict[str, Any]:
    return asyncio.run(send_password_reset_code(recipient=recipient, code=code))


@celery_app.task(name="yummydoors.notifications.send_email", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_email_task(self, recipient: str, subject: str, body: str) -> dict[str, Any]:
    return asyncio.run(send_email_message(recipient=recipient, subject=subject, body=body))


@celery_app.task(name="yummydoors.notifications.send_user_push", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_user_push_task(self, user_id: int, payload: dict[str, Any]) -> None:
    asyncio.run(_send_user_notification_async(user_id=user_id, payload=payload))


@celery_app.task(name="yummydoors.notifications.send_merchant_push", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_merchant_push_task(self, restaurant_id: int, payload: dict[str, Any]) -> None:
    asyncio.run(_send_merchant_notification_async(restaurant_id=restaurant_id, payload=payload))
