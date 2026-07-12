from __future__ import annotations

from celery import shared_task


@shared_task(name="app.tasks.rider_dispatch.expire_offer")
def expire_dispatch_offer(offer_id: int) -> dict[str, int | str]:
    from app.db.session import SessionLocal
    from app.modules.rider_dispatch.service import RiderDispatchService

    async def _run() -> None:
        async with SessionLocal() as session:
            service = RiderDispatchService(session)
            await service.expire_offer(offer_id=offer_id)

    import asyncio

    asyncio.run(_run())
    return {"offer_id": offer_id, "status": "processed"}

