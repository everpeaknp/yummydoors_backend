from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order, OrderStatus


async def get_lifetime_delivery_count(session: AsyncSession, rider_user_id: int) -> int:
    result = await session.execute(
        select(func.count(Order.id)).where(
            Order.rider_user_id == rider_user_id,
            Order.status == OrderStatus.delivered,
        )
    )
    return int(result.scalar_one())
