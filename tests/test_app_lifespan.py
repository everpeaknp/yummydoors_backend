import asyncio

import pytest

from app.main import lifespan, realtime_bus


@pytest.mark.asyncio
async def test_lifespan_enters_without_waiting_for_realtime_start(monkeypatch):
    async def fake_start():
        await asyncio.sleep(0.1)

    async def fake_stop():
        return None

    monkeypatch.setattr(realtime_bus, "start", fake_start)
    monkeypatch.setattr(realtime_bus, "stop", fake_stop)

    ctx = lifespan(object())
    await asyncio.wait_for(ctx.__aenter__(), timeout=0.05)
    await ctx.__aexit__(None, None, None)
