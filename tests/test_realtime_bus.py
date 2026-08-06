import asyncio

import pytest

from app.modules.realtime.bus import RedisRealtimeBus


class _FakePubSub:
    def __init__(self):
        self.subscribed = set()
        self._messages = asyncio.Queue()

    async def subscribe(self, *channels):
        self.subscribed.update(channels)

    async def get_message(self, *, ignore_subscribe_messages=True, timeout=1.0):
        try:
            return await asyncio.wait_for(self._messages.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def close(self):
        pass

    def push(self, channel, data):
        self._messages.put_nowait({"channel": channel, "data": data})


class _FakeRedisClient:
    def __init__(self):
        self.pubsub_instance = _FakePubSub()
        self.published = []

    async def ping(self):
        return True

    def pubsub(self):
        return self.pubsub_instance

    async def publish(self, channel, data):
        self.published.append((channel, data))

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_realtime_bus_start_is_non_fatal_when_redis_is_unavailable(monkeypatch):
    def _raise(*args, **kwargs):
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr("app.modules.realtime.bus.redis.from_url", _raise)

    bus = RedisRealtimeBus("redis://redis:6379/0", initial_retry_seconds=60)
    await bus.start()

    # A failed initial connection must not disable the bus permanently: it
    # stays "started" (intent to run) and schedules a background reconnect
    # attempt instead of requiring a manual process restart to recover.
    assert bus._started is True
    assert bus.is_available is False
    assert bus._client is None
    assert bus._pubsub is None
    assert bus._reconnect_task is not None
    assert not bus._reconnect_task.done()

    await bus.stop()
    assert bus._started is False
    assert bus._reconnect_task is None


@pytest.mark.asyncio
async def test_realtime_bus_publish_is_noop_when_bus_not_started():
    bus = RedisRealtimeBus("redis://redis:6379/0")

    await bus.publish("yummydoors:test", {"hello": "world"})

    assert bus._client is None


@pytest.mark.asyncio
async def test_realtime_bus_reconnects_and_delivers_after_transient_failure(monkeypatch):
    attempts = {"count": 0}
    fake_client = _FakeRedisClient()

    def _from_url(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ConnectionError("redis unavailable")
        return fake_client

    monkeypatch.setattr("app.modules.realtime.bus.redis.from_url", _from_url)

    received = []

    async def handler(payload):
        received.append(payload)

    bus = RedisRealtimeBus("redis://redis:6379/0", initial_retry_seconds=0.05, max_retry_seconds=0.1)
    bus.register_handler("yummydoors:test", handler)

    await bus.start()
    assert bus.is_available is False

    # Wait for the background reconnect loop to succeed on its second attempt.
    for _ in range(50):
        if bus.is_available:
            break
        await asyncio.sleep(0.05)
    assert bus.is_available is True
    assert attempts["count"] >= 2

    fake_client.pubsub_instance.push("yummydoors:test", '{"hello": "world"}')
    for _ in range(20):
        if received:
            break
        await asyncio.sleep(0.05)
    assert received == [{"hello": "world"}]

    await bus.publish("yummydoors:test", {"ping": True})
    assert fake_client.published == [("yummydoors:test", '{"ping": true}')]

    await bus.stop()
    assert bus.is_available is False
    assert bus._reconnect_task is None
