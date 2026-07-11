from __future__ import annotations

import asyncio
from typing import Any

from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.modules.auth.notifications import send_email_message, send_password_reset_code
from app.modules.notifications.service import NotificationService


async def _send_user_notification_async(user_id: int, payload: dict[str, Any]) -> None:
    async with AsyncSessionLocal() as session:
        service = NotificationService(session)
        await service.send_web_push_to_user(user_id=user_id, payload=payload)
        await service.send_fcm_to_user(user_id=user_id, payload=payload)


async def _send_merchant_notification_async(restaurant_id: int, payload: dict[str, Any]) -> None:
    async with AsyncSessionLocal() as session:
        service = NotificationService(session)
        await service.send_web_push_to_merchants(restaurant_id=restaurant_id, payload=payload)
        await service.send_fcm_to_merchants(restaurant_id=restaurant_id, payload=payload)


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
