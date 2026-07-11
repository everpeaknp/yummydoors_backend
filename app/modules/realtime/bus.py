from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

RealtimeHandler = Callable[[dict[str, Any]], Awaitable[None]]

ORDER_MERCHANT_CHANNEL = "yummydoors:orders:merchant"
ORDER_CUSTOMER_CHANNEL = "yummydoors:orders:customer"
ORDER_RIDER_CHANNEL = "yummydoors:orders:rider"
MESSAGE_MERCHANT_CHANNEL = "yummydoors:messages:merchant"
MESSAGE_CUSTOMER_CHANNEL = "yummydoors:messages:customer"


class RedisRealtimeBus:
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._handlers: dict[str, RealtimeHandler] = {}
        self._client: redis.Redis[str] | None = None
        self._pubsub: redis.client.PubSub[str] | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._started = False
        self._subscribed_channels: set[str] = set()

    def register_handler(self, channel: str, handler: RealtimeHandler) -> None:
        self._handlers[channel] = handler
        if self._started and self._pubsub is not None and channel not in self._subscribed_channels:
            asyncio.create_task(self._subscribe_channel(channel))

    async def start(self) -> None:
        if self._started:
            return

        try:
            self._client = redis.from_url(self._redis_url, decode_responses=True)
            self._pubsub = self._client.pubsub()
            await self._subscribe_all()
            self._listener_task = asyncio.create_task(self._listen_loop())
            self._started = True
            logger.info("redis realtime bus started channels=%s", list(self._handlers))
        except Exception:
            logger.warning(
                "redis realtime bus unavailable; realtime delivery disabled",
                exc_info=True,
            )
            await self.stop()

    async def stop(self) -> None:
        self._started = False

        if self._listener_task is not None:
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None

        if self._pubsub is not None:
            await self._pubsub.close()
            self._pubsub = None

        if self._client is not None:
            await self._client.aclose()
            self._client = None

        self._subscribed_channels.clear()

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        if self._client is None:
            logger.debug("dropping realtime payload because bus is not started channel=%s", channel)
            return

        await self._client.publish(channel, json.dumps(payload, default=str))

    async def _subscribe_all(self) -> None:
        if self._pubsub is None:
            return

        channels = [channel for channel in self._handlers if channel not in self._subscribed_channels]
        if not channels:
            return

        await self._pubsub.subscribe(*channels)
        self._subscribed_channels.update(channels)

    async def _subscribe_channel(self, channel: str) -> None:
        if self._pubsub is None or channel in self._subscribed_channels:
            return

        await self._pubsub.subscribe(channel)
        self._subscribed_channels.add(channel)

    async def _listen_loop(self) -> None:
        if self._pubsub is None:
            return

        try:
            while self._started:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if not message:
                    continue

                channel = message.get("channel")
                if not isinstance(channel, str):
                    continue

                handler = self._handlers.get(channel)
                if handler is None:
                    continue

                payload = message.get("data")
                if not isinstance(payload, str):
                    continue

                try:
                    data = json.loads(payload)
                except Exception:
                    logger.exception("failed to decode realtime payload for channel %s", channel)
                    continue

                asyncio.create_task(self._dispatch(channel, handler, data))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("realtime bus listener crashed")

    async def _dispatch(self, channel: str, handler: RealtimeHandler, payload: dict[str, Any]) -> None:
        try:
            await handler(payload)
        except Exception:
            logger.exception("failed to dispatch realtime event channel=%s", channel)


realtime_bus = RedisRealtimeBus(
    settings.redis_url,
)
