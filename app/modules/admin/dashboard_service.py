from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.orders.models import Order, OrderStatus
from app.modules.restaurants.models import Restaurant
from app.modules.rider_applications.models import RiderApplication
from app.modules.workspaces.models import MerchantApplication


class AdminDashboardSummary(BaseModel):
    orders_today: int
    orders_this_week: int
    revenue_today: float
    revenue_this_week: float
    active_restaurants: int
    total_restaurants: int
    pending_merchant_applications: int
    pending_rider_applications: int
    orders_in_flight: int
    cancelled_orders_this_week: int


async def build_dashboard_summary(session: AsyncSession) -> AdminDashboardSummary:
    """Real, DB-backed KPIs for the admin dashboard overview, replacing the
    previous static list-of-links page that carried no live numbers at all."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    delivered_or_active = OrderStatus.cancelled

    orders_today_result = await session.execute(
        select(func.count()).select_from(Order).where(Order.created_at >= today_start)
    )
    orders_this_week_result = await session.execute(
        select(func.count()).select_from(Order).where(Order.created_at >= week_start)
    )
    revenue_today_result = await session.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
            Order.created_at >= today_start, Order.status != delivered_or_active
        )
    )
    revenue_this_week_result = await session.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
            Order.created_at >= week_start, Order.status != delivered_or_active
        )
    )
    active_restaurants_result = await session.execute(
        select(func.count()).select_from(Restaurant).where(Restaurant.status == "active")
    )
    total_restaurants_result = await session.execute(select(func.count()).select_from(Restaurant))
    pending_merchant_applications_result = await session.execute(
        select(func.count()).select_from(MerchantApplication).where(MerchantApplication.status == "submitted")
    )
    pending_rider_applications_result = await session.execute(
        select(func.count()).select_from(RiderApplication).where(RiderApplication.status == "submitted")
    )
    orders_in_flight_result = await session.execute(
        select(func.count())
        .select_from(Order)
        .where(Order.status.in_([OrderStatus.placed, OrderStatus.preparing, OrderStatus.toPay]))
    )
    cancelled_this_week_result = await session.execute(
        select(func.count())
        .select_from(Order)
        .where(Order.created_at >= week_start, Order.status == OrderStatus.cancelled)
    )

    return AdminDashboardSummary(
        orders_today=int(orders_today_result.scalar_one() or 0),
        orders_this_week=int(orders_this_week_result.scalar_one() or 0),
        revenue_today=float(revenue_today_result.scalar_one() or 0.0),
        revenue_this_week=float(revenue_this_week_result.scalar_one() or 0.0),
        active_restaurants=int(active_restaurants_result.scalar_one() or 0),
        total_restaurants=int(total_restaurants_result.scalar_one() or 0),
        pending_merchant_applications=int(pending_merchant_applications_result.scalar_one() or 0),
        pending_rider_applications=int(pending_rider_applications_result.scalar_one() or 0),
        orders_in_flight=int(orders_in_flight_result.scalar_one() or 0),
        cancelled_orders_this_week=int(cancelled_this_week_result.scalar_one() or 0),
    )
