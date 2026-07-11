import pytest

from app.modules.realtime.bus import RedisRealtimeBus


@pytest.mark.asyncio
async def test_realtime_bus_start_is_non_fatal_when_redis_is_unavailable(monkeypatch):
    def _raise(*args, **kwargs):
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr("app.modules.realtime.bus.redis.from_url", _raise)

    bus = RedisRealtimeBus("redis://redis:6379/0")
    await bus.start()

    assert bus._started is False
    assert bus._client is None
    assert bus._pubsub is None


@pytest.mark.asyncio
async def test_realtime_bus_publish_is_noop_when_bus_not_started():
    bus = RedisRealtimeBus("redis://redis:6379/0")

    await bus.publish("yummydoors:test", {"hello": "world"})

    assert bus._client is None
