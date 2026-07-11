from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "yummydoors",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.notifications"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_default_queue="yummydoors",
)
