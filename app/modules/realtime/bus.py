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


async def _safe_close_pubsub(pubsub: "redis.client.PubSub[str]") -> None:
    with suppress(Exception):
        await pubsub.close()


async def _safe_close_client(client: "redis.Redis[str]") -> None:
    with suppress(Exception):
        await client.aclose()


class RedisRealtimeBus:
    """Redis-backed pub/sub bus with automatic reconnection.

    `start()`/`stop()` control whether the bus *should* be running. Within
    that, `_connected` tracks whether there is currently a live Redis
    connection and listener task. A dropped connection (initial connect
    failure, or the listener losing the connection mid-stream) schedules a
    background reconnect loop with capped exponential backoff instead of
    permanently disabling realtime delivery until the process restarts.
    """

    def __init__(
        self,
        redis_url: str,
        *,
        initial_retry_seconds: float = 5.0,
        max_retry_seconds: float = 60.0,
    ):
        self._redis_url = redis_url
        self._handlers: dict[str, RealtimeHandler] = {}
        self._client: redis.Redis[str] | None = None
        self._pubsub: redis.client.PubSub[str] | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._started = False
        self._connected = False
        self._subscribed_channels: set[str] = set()
        self._initial_retry_seconds = initial_retry_seconds
        self._max_retry_seconds = max_retry_seconds

    @property
    def is_available(self) -> bool:
        return self._connected and self._client is not None

    def register_handler(self, channel: str, handler: RealtimeHandler) -> None:
        self._handlers[channel] = handler
        if self._connected and self._pubsub is not None and channel not in self._subscribed_channels:
            asyncio.create_task(self._subscribe_channel(channel))

    async def start(self) -> None:
        if self._started:
            return

        self._started = True
        connected = await self._connect_once()
        if not connected:
            self._schedule_reconnect(self._initial_retry_seconds)

    async def stop(self) -> None:
        self._started = False

        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None

        await self._disconnect()

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        client = self._client
        if client is None or not self._connected:
            logger.debug("dropping realtime payload because bus is not connected channel=%s", channel)
            return

        try:
            await client.publish(channel, json.dumps(payload, default=str))
        except Exception:
            logger.warning(
                "failed to publish realtime payload; connection may be down channel=%s",
                channel,
                exc_info=True,
            )
            if self._connected:
                await self._disconnect(keep_started=True)
                self._schedule_reconnect(self._initial_retry_seconds)

    async def _connect_once(self) -> bool:
        try:
            client = redis.from_url(self._redis_url, decode_responses=True)
            await client.ping()
            pubsub = client.pubsub()

            self._client = client
            self._pubsub = pubsub
            self._subscribed_channels = set()
            await self._subscribe_all()

            self._connected = True
            self._listener_task = asyncio.create_task(self._listen_loop())
            logger.info("redis realtime bus connected channels=%s", list(self._handlers))
            return True
        except Exception:
            logger.warning(
                "redis realtime bus connection failed; realtime delivery degraded, will retry",
                exc_info=True,
            )
            await self._disconnect(keep_started=True)
            return False

    async def _disconnect(self, *, keep_started: bool = False) -> None:
        self._connected = False
        if not keep_started:
            self._started = False

        listener_task = self._listener_task
        self._listener_task = None
        if listener_task is not None and listener_task is not asyncio.current_task():
            listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await listener_task

        if self._pubsub is not None:
            await _safe_close_pubsub(self._pubsub)
            self._pubsub = None

        if self._client is not None:
            await _safe_close_client(self._client)
            self._client = None

        self._subscribed_channels.clear()

    def _schedule_reconnect(self, delay: float) -> None:
        if not self._started:
            return
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(self._reconnect_loop(delay))

    async def _reconnect_loop(self, delay: float) -> None:
        current_delay = delay
        try:
            while self._started and not self._connected:
                await asyncio.sleep(current_delay)
                if not self._started or self._connected:
                    return
                if await self._connect_once():
                    return
                current_delay = min(current_delay * 2, self._max_retry_seconds)
        except asyncio.CancelledError:
            raise

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
        pubsub = self._pubsub
        if pubsub is None:
            return

        lost_connection = False
        try:
            while self._connected:
                try:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.warning(
                        "redis realtime bus listener lost connection; scheduling reconnect",
                        exc_info=True,
                    )
                    lost_connection = True
                    break

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
        finally:
            if lost_connection and self._connected:
                self._connected = False
                self._listener_task = None
                old_pubsub, self._pubsub = self._pubsub, None
                old_client, self._client = self._client, None
                self._subscribed_channels.clear()
                if old_pubsub is not None:
                    asyncio.create_task(_safe_close_pubsub(old_pubsub))
                if old_client is not None:
                    asyncio.create_task(_safe_close_client(old_client))
                self._schedule_reconnect(self._initial_retry_seconds)

    async def _dispatch(self, channel: str, handler: RealtimeHandler, payload: dict[str, Any]) -> None:
        try:
            await handler(payload)
        except Exception:
            logger.exception("failed to dispatch realtime event channel=%s", channel)


realtime_bus = RedisRealtimeBus(
    settings.redis_url,
)
