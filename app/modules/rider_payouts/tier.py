from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order, OrderStatus


@dataclass(frozen=True)
class RiderTier:
    name: str
    label: str
    min_deliveries: int
    commission_rate_percent: float
    # Lower = offered first within the same dispatch tier (open/platform) —
    # higher-tier riders get first crack at a broadcast job instead of
    # everyone seeing it at the identical instant.
    dispatch_priority: int


# Ordered highest -> lowest so tier_for_delivery_count can walk down and
# return the first (best) tier the rider qualifies for.
RIDER_TIERS: tuple[RiderTier, ...] = (
    RiderTier(name="platinum", label="Platinum", min_deliveries=100, commission_rate_percent=15.0, dispatch_priority=0),
    RiderTier(name="basic", label="Basic", min_deliveries=50, commission_rate_percent=18.0, dispatch_priority=1),
    RiderTier(name="new", label="New", min_deliveries=0, commission_rate_percent=20.0, dispatch_priority=2),
)


def tier_for_delivery_count(delivery_count: int) -> RiderTier:
    for tier in RIDER_TIERS:
        if delivery_count >= tier.min_deliveries:
            return tier
    return RIDER_TIERS[-1]


async def get_lifetime_delivery_count(session: AsyncSession, rider_user_id: int) -> int:
    result = await session.execute(
        select(func.count(Order.id)).where(
            Order.rider_user_id == rider_user_id,
            Order.status == OrderStatus.delivered,
        )
    )
    return int(result.scalar_one())


async def get_rider_tier(session: AsyncSession, rider_user_id: int) -> RiderTier:
    count = await get_lifetime_delivery_count(session, rider_user_id)
    return tier_for_delivery_count(count)


async def get_tiers_for_riders(session: AsyncSession, rider_user_ids: list[int]) -> dict[int, RiderTier]:
    """Batched version for dispatch candidate building — avoids one query
    per candidate rider."""
    if not rider_user_ids:
        return {}
    result = await session.execute(
        select(Order.rider_user_id, func.count(Order.id))
        .where(Order.rider_user_id.in_(rider_user_ids), Order.status == OrderStatus.delivered)
        .group_by(Order.rider_user_id)
    )
    counts = dict(result.all())
    return {uid: tier_for_delivery_count(counts.get(uid, 0)) for uid in rider_user_ids}
