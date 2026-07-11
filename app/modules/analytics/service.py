from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Iterable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.catalog.models import MenuItem
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.restaurants.models import Category, Restaurant

from .schemas import (
    AnalyticsBreakdownItem,
    AnalyticsDateRange,
    AnalyticsDailyPoint,
    AnalyticsLoyaltySummary,
    AnalyticsPeriod,
    AnalyticsStatusBreakdown,
    AnalyticsSummary,
    CustomerAnalyticsResponse,
    MerchantAnalyticsResponse,
)

LOYALTY_RATE = Decimal("0.05")


@dataclass(frozen=True)
class OrderAnalyticsRow:
    order_id: int
    restaurant_id: int
    restaurant_name: str
    status: OrderStatus
    total_price: Decimal
    subtotal_amount: Decimal
    created_at: datetime


@dataclass(frozen=True)
class ItemAnalyticsRow:
    order_id: int
    restaurant_id: int
    restaurant_name: str
    status: OrderStatus
    order_total: Decimal
    order_subtotal: Decimal
    created_at: datetime
    menu_item_id: int | None
    item_name: str
    category_id: int | None
    category_name: str | None
    quantity: int
    unit_price: Decimal


def calculate_loyalty_points(amount: Decimal | float | int) -> int:
    return int(Decimal(str(amount or 0)) * LOYALTY_RATE)


def resolve_analytics_range(
    period: AnalyticsPeriod,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    now: datetime | None = None,
) -> AnalyticsDateRange:
    current = now or datetime.now(UTC)
    today = current.date()

    if period == AnalyticsPeriod.today:
        start = end = today
        label = "Today"
    elif period == AnalyticsPeriod.yesterday:
        start = end = today - timedelta(days=1)
        label = "Yesterday"
    elif period == AnalyticsPeriod.last_7_days:
        start = today - timedelta(days=6)
        end = today
        label = "Last 7 days"
    elif period == AnalyticsPeriod.last_week:
        current_week_start = today - timedelta(days=today.weekday())
        start = current_week_start - timedelta(days=7)
        end = current_week_start - timedelta(days=1)
        label = "Last week"
    elif period == AnalyticsPeriod.last_30_days:
        start = today - timedelta(days=29)
        end = today
        label = "Last 30 days"
    elif period == AnalyticsPeriod.last_month:
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
        label = "Last month"
    elif period == AnalyticsPeriod.this_year:
        start = today.replace(month=1, day=1)
        end = today
        label = "This year"
    else:
        if start_date is None or end_date is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date and end_date are required for custom analytics ranges.",
            )
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be on or before end_date.",
            )
        start = start_date
        end = end_date
        label = f"{start.isoformat()} to {end.isoformat()}"

    return AnalyticsDateRange(period=period, label=label, start_date=start, end_date=end)


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def _end_of_day(day: date) -> datetime:
    return datetime.combine(day, time.max, tzinfo=UTC)


def _money(value: Decimal | float | int | None) -> Decimal:
    return Decimal(str(value or 0))


def _status_bucket(status_value: OrderStatus | str) -> str:
    status_text = status_value.value if isinstance(status_value, OrderStatus) else str(status_value)
    if status_text == OrderStatus.delivered.value:
        return "delivered"
    if status_text == OrderStatus.cancelled.value:
        return "cancelled"
    return "pending"


def _date_range_days(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _default_daily_map(start: date, end: date) -> dict[date, AnalyticsDailyPoint]:
    return {
        day: AnalyticsDailyPoint(date=day)
        for day in _date_range_days(start, end)
    }


def _finalize_summary(
    *,
    orders_count: int,
    delivered_orders_count: int,
    cancelled_orders_count: int,
    pending_orders_count: int,
    refunded_orders_count: int = 0,
    gross_spend: Decimal,
    net_spend: Decimal,
    cancelled_spend: Decimal,
    pending_spend: Decimal,
    refunded_spend: Decimal = Decimal("0"),
) -> AnalyticsSummary:
    average_order_value = round(float(net_spend) / delivered_orders_count, 2) if delivered_orders_count else 0.0
    return AnalyticsSummary(
        orders_count=orders_count,
        delivered_orders_count=delivered_orders_count,
        cancelled_orders_count=cancelled_orders_count,
        pending_orders_count=pending_orders_count,
        refunded_orders_count=refunded_orders_count,
        gross_spend=round(float(gross_spend), 2),
        net_spend=round(float(net_spend), 2),
        cancelled_spend=round(float(cancelled_spend), 2),
        pending_spend=round(float(pending_spend), 2),
        refunded_spend=round(float(refunded_spend), 2),
        average_order_value=average_order_value,
    )


def _build_order_rows(order_rows: Iterable[dict[str, Any]]) -> list[OrderAnalyticsRow]:
    rows: list[OrderAnalyticsRow] = []
    for row in order_rows:
        rows.append(
            OrderAnalyticsRow(
                order_id=int(row["order_id"]),
                restaurant_id=int(row["restaurant_id"]),
                restaurant_name=str(row["restaurant_name"]),
                status=row["status"],
                total_price=_money(row["total_price"]),
                subtotal_amount=_money(row["subtotal_amount"]),
                created_at=row["created_at"],
            )
        )
    return rows


def _build_item_rows(item_rows: Iterable[dict[str, Any]]) -> list[ItemAnalyticsRow]:
    rows: list[ItemAnalyticsRow] = []
    for row in item_rows:
        rows.append(
            ItemAnalyticsRow(
                order_id=int(row["order_id"]),
                restaurant_id=int(row["restaurant_id"]),
                restaurant_name=str(row["restaurant_name"]),
                status=row["status"],
                order_total=_money(row["order_total"]),
                order_subtotal=_money(row["order_subtotal"]),
                created_at=row["created_at"],
                menu_item_id=(int(row["menu_item_id"]) if row["menu_item_id"] is not None else None),
                item_name=str(row["item_name"]),
                category_id=(int(row["category_id"]) if row["category_id"] is not None else None),
                category_name=(str(row["category_name"]) if row["category_name"] is not None else None),
                quantity=int(row["quantity"]),
                unit_price=_money(row["unit_price"]),
            )
        )
    return rows


def _allocate_item_spend(row: ItemAnalyticsRow) -> Decimal:
    line_subtotal = _money(row.unit_price) * Decimal(row.quantity)
    if row.order_subtotal > 0:
        return (_money(row.order_total) * line_subtotal) / row.order_subtotal
    return line_subtotal


def _build_daily_points(
    rows: list[OrderAnalyticsRow],
    start_date: date,
    end_date: date,
) -> list[AnalyticsDailyPoint]:
    daily = _default_daily_map(start_date, end_date)
    for row in rows:
        point = daily[row.created_at.date()]
        bucket = _status_bucket(row.status)
        amount = row.total_price
        point.orders_count += 1
        point.gross_spend = round(float(Decimal(str(point.gross_spend)) + amount), 2)
        if bucket == "delivered":
            point.net_spend = round(float(Decimal(str(point.net_spend)) + amount), 2)
        elif bucket == "cancelled":
            point.cancelled_spend = round(float(Decimal(str(point.cancelled_spend)) + amount), 2)
        else:
            point.pending_spend = round(float(Decimal(str(point.pending_spend)) + amount), 2)
    return [daily[day] for day in sorted(daily)]


def _build_status_breakdown(rows: list[OrderAnalyticsRow]) -> list[AnalyticsStatusBreakdown]:
    buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {"orders_count": 0, "spend": Decimal("0")})
    for row in rows:
        bucket = _status_bucket(row.status)
        entry = buckets[bucket]
        entry["orders_count"] += 1
        entry["spend"] += row.total_price
    order = {"delivered": 0, "pending": 1, "cancelled": 2}
    return [
        AnalyticsStatusBreakdown(status=status_name, orders_count=data["orders_count"], spend=round(float(data["spend"]), 2))
        for status_name, data in sorted(buckets.items(), key=lambda item: order.get(item[0], 99))
    ]


def _build_item_breakdown(
    item_rows: list[ItemAnalyticsRow],
    *,
    key_getter,
) -> list[AnalyticsBreakdownItem]:
    buckets: dict[tuple[int | None, str], dict[str, Any]] = defaultdict(
        lambda: {
            "id": None,
            "name": "",
            "orders_count": 0,
            "quantity": 0,
            "net_quantity": 0,
            "cancelled_quantity": 0,
            "pending_quantity": 0,
            "gross_spend": Decimal("0"),
            "net_spend": Decimal("0"),
            "cancelled_spend": Decimal("0"),
            "pending_spend": Decimal("0"),
        }
    )
    for row in item_rows:
        key = key_getter(row)
        bucket = buckets[key]
        if not bucket["name"]:
            bucket["id"] = key[0]
            bucket["name"] = key[1]
        bucket["orders_count"] += 1
        bucket["quantity"] += row.quantity
        amount = _allocate_item_spend(row)
        bucket["gross_spend"] += amount
        status_bucket = _status_bucket(row.status)
        if status_bucket == "delivered":
            bucket["net_quantity"] += row.quantity
            bucket["net_spend"] += amount
        elif status_bucket == "cancelled":
            bucket["cancelled_quantity"] += row.quantity
            bucket["cancelled_spend"] += amount
        else:
            bucket["pending_quantity"] += row.quantity
            bucket["pending_spend"] += amount

    items: list[AnalyticsBreakdownItem] = []
    for data in buckets.values():
        if not data["name"]:
            continue
        items.append(
            AnalyticsBreakdownItem(
                id=data["id"],
                name=data["name"],
                orders_count=data["orders_count"],
                quantity=data["net_quantity"] or data["quantity"],
                gross_spend=round(float(data["gross_spend"]), 2),
                net_spend=round(float(data["net_spend"]), 2),
                cancelled_spend=round(float(data["cancelled_spend"]), 2),
                pending_spend=round(float(data["pending_spend"]), 2),
            )
        )
    items.sort(key=lambda item: (-item.net_spend, -item.quantity, item.name.lower()))
    return items


def _build_customer_breakdowns(
    order_rows: list[OrderAnalyticsRow],
    item_rows: list[ItemAnalyticsRow],
) -> tuple[list[AnalyticsBreakdownItem], list[AnalyticsBreakdownItem], list[AnalyticsBreakdownItem]]:
    restaurant_map: dict[tuple[int, str], dict[str, Any]] = defaultdict(
        lambda: {
            "id": None,
            "name": "",
            "orders_count": 0,
            "gross_spend": Decimal("0"),
            "net_spend": Decimal("0"),
            "cancelled_spend": Decimal("0"),
            "pending_spend": Decimal("0"),
        }
    )
    for row in order_rows:
        key = (row.restaurant_id, row.restaurant_name)
        bucket = restaurant_map[key]
        bucket["id"] = row.restaurant_id
        bucket["name"] = row.restaurant_name
        bucket["orders_count"] += 1
        bucket["gross_spend"] += row.total_price
        status_bucket = _status_bucket(row.status)
        if status_bucket == "delivered":
            bucket["net_spend"] += row.total_price
        elif status_bucket == "cancelled":
            bucket["cancelled_spend"] += row.total_price
        else:
            bucket["pending_spend"] += row.total_price

    restaurant_breakdown = [
        AnalyticsBreakdownItem(
            id=data["id"],
            name=data["name"],
            orders_count=data["orders_count"],
            gross_spend=round(float(data["gross_spend"]), 2),
            net_spend=round(float(data["net_spend"]), 2),
            cancelled_spend=round(float(data["cancelled_spend"]), 2),
            pending_spend=round(float(data["pending_spend"]), 2),
        )
        for data in restaurant_map.values()
    ]
    restaurant_breakdown.sort(key=lambda item: (-item.net_spend, -item.orders_count, item.name.lower()))

    category_map: dict[tuple[int | None, str], dict[str, Any]] = defaultdict(
        lambda: {
            "id": None,
            "name": "",
            "orders_count": 0,
            "quantity": 0,
            "gross_spend": Decimal("0"),
            "net_spend": Decimal("0"),
            "cancelled_spend": Decimal("0"),
            "pending_spend": Decimal("0"),
        }
    )
    food_map: dict[tuple[int | None, str], dict[str, Any]] = defaultdict(
        lambda: {
            "id": None,
            "name": "",
            "orders_count": 0,
            "quantity": 0,
            "gross_spend": Decimal("0"),
            "net_spend": Decimal("0"),
            "cancelled_spend": Decimal("0"),
            "pending_spend": Decimal("0"),
        }
    )

    for row in item_rows:
        amount = _allocate_item_spend(row)
        status_bucket = _status_bucket(row.status)

        category_key = (row.category_id, row.category_name or "Uncategorized")
        category_bucket = category_map[category_key]
        category_bucket["id"] = row.category_id
        category_bucket["name"] = row.category_name or "Uncategorized"
        category_bucket["orders_count"] += 1
        category_bucket["quantity"] += row.quantity
        category_bucket["gross_spend"] += amount
        if status_bucket == "delivered":
            category_bucket["net_spend"] += amount
        elif status_bucket == "cancelled":
            category_bucket["cancelled_spend"] += amount
        else:
            category_bucket["pending_spend"] += amount

        food_key = (row.menu_item_id, row.item_name)
        food_bucket = food_map[food_key]
        food_bucket["id"] = row.menu_item_id
        food_bucket["name"] = row.item_name
        food_bucket["orders_count"] += 1
        food_bucket["quantity"] += row.quantity
        food_bucket["gross_spend"] += amount
        if status_bucket == "delivered":
            food_bucket["net_spend"] += amount
        elif status_bucket == "cancelled":
            food_bucket["cancelled_spend"] += amount
        else:
            food_bucket["pending_spend"] += amount

    category_breakdown = [
        AnalyticsBreakdownItem(
            id=data["id"],
            name=data["name"],
            orders_count=data["orders_count"],
            quantity=data["quantity"],
            gross_spend=round(float(data["gross_spend"]), 2),
            net_spend=round(float(data["net_spend"]), 2),
            cancelled_spend=round(float(data["cancelled_spend"]), 2),
            pending_spend=round(float(data["pending_spend"]), 2),
        )
        for data in category_map.values()
        if data["name"]
    ]
    category_breakdown.sort(key=lambda item: (-item.net_spend, -item.quantity, item.name.lower()))

    food_breakdown = [
        AnalyticsBreakdownItem(
            id=data["id"],
            name=data["name"],
            orders_count=data["orders_count"],
            quantity=data["quantity"],
            gross_spend=round(float(data["gross_spend"]), 2),
            net_spend=round(float(data["net_spend"]), 2),
            cancelled_spend=round(float(data["cancelled_spend"]), 2),
            pending_spend=round(float(data["pending_spend"]), 2),
        )
        for data in food_map.values()
        if data["name"]
    ]
    food_breakdown.sort(key=lambda item: (-item.net_spend, -item.quantity, item.name.lower()))
    return restaurant_breakdown, category_breakdown, food_breakdown


async def _load_order_rows(
    session: AsyncSession,
    *,
    start_dt: datetime,
    end_dt: datetime,
    restaurant_id: int | None = None,
    customer_id: int | None = None,
) -> list[OrderAnalyticsRow]:
    stmt = (
        select(
            Order.id.label("order_id"),
            Order.restaurant_id.label("restaurant_id"),
            Restaurant.name.label("restaurant_name"),
            Order.status.label("status"),
            Order.total_price.label("total_price"),
            Order.subtotal_amount.label("subtotal_amount"),
            Order.created_at.label("created_at"),
        )
        .join(Restaurant, Restaurant.id == Order.restaurant_id)
        .where(Order.created_at >= start_dt, Order.created_at <= end_dt)
        .order_by(Order.created_at.asc(), Order.id.asc())
    )
    if restaurant_id is not None:
        stmt = stmt.where(Order.restaurant_id == restaurant_id)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)

    result = await session.execute(stmt)
    return _build_order_rows(result.mappings().all())


async def _load_item_rows(
    session: AsyncSession,
    *,
    start_dt: datetime,
    end_dt: datetime,
    restaurant_id: int | None = None,
    customer_id: int | None = None,
) -> list[ItemAnalyticsRow]:
    stmt = (
        select(
            Order.id.label("order_id"),
            Order.restaurant_id.label("restaurant_id"),
            Restaurant.name.label("restaurant_name"),
            Order.status.label("status"),
            Order.total_price.label("order_total"),
            Order.subtotal_amount.label("order_subtotal"),
            Order.created_at.label("created_at"),
            OrderItem.menu_item_id.label("menu_item_id"),
            func.coalesce(OrderItem.name, MenuItem.name).label("item_name"),
            MenuItem.category_id.label("category_id"),
            Category.name.label("category_name"),
            OrderItem.quantity.label("quantity"),
            OrderItem.price.label("unit_price"),
        )
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Restaurant, Restaurant.id == Order.restaurant_id)
        .outerjoin(MenuItem, MenuItem.id == OrderItem.menu_item_id)
        .outerjoin(Category, Category.id == MenuItem.category_id)
        .where(Order.created_at >= start_dt, Order.created_at <= end_dt)
        .order_by(Order.created_at.asc(), Order.id.asc(), OrderItem.id.asc())
    )
    if restaurant_id is not None:
        stmt = stmt.where(Order.restaurant_id == restaurant_id)
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)

    result = await session.execute(stmt)
    return _build_item_rows(result.mappings().all())


def _loyalty_summary(user: User, points_in_period: int, order_count: int, spent: Decimal) -> AnalyticsLoyaltySummary:
    return AnalyticsLoyaltySummary(
        current_points=int(user.loyalty_points or 0),
        total_orders=int(user.total_orders or 0),
        total_spent=round(float(user.total_spent or 0), 2),
        lifetime_points_earned=int(user.loyalty_points_earned or 0),
        lifetime_points_redeemed=int(user.loyalty_points_redeemed or 0),
        points_earned_in_period=points_in_period,
        points_rate=float(LOYALTY_RATE),
    )


def _sum_orders(rows: list[OrderAnalyticsRow]) -> tuple[AnalyticsSummary, dict[str, Decimal], dict[date, AnalyticsDailyPoint], dict[int, AnalyticsBreakdownItem]]:
    daily = _default_daily_map(rows[0].created_at.date(), rows[0].created_at.date()) if rows else {}
    status_counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"orders_count": 0, "spend": Decimal("0")})
    restaurant_map: dict[int, AnalyticsBreakdownItem] = {}

    orders_count = delivered_count = cancelled_count = pending_count = 0
    gross = net = cancelled = pending = Decimal("0")

    for row in rows:
        bucket = _status_bucket(row.status)
        amount = row.total_price
        orders_count += 1
        gross += amount
        point = daily.setdefault(
            row.created_at.date(),
            AnalyticsDailyPoint(date=row.created_at.date()),
        )
        point.orders_count += 1
        point.gross_spend = round(float(Decimal(str(point.gross_spend)) + amount), 2)

        status_entry = status_counts[bucket]
        status_entry["orders_count"] += 1
        status_entry["spend"] += amount

        restaurant = restaurant_map.setdefault(
            row.restaurant_id,
            AnalyticsBreakdownItem(id=row.restaurant_id, name=row.restaurant_name),
        )
        restaurant.orders_count += 1
        restaurant.gross_spend = round(float(Decimal(str(restaurant.gross_spend)) + amount), 2)

        if bucket == "delivered":
            delivered_count += 1
            net += amount
            point.net_spend = round(float(Decimal(str(point.net_spend)) + amount), 2)
            restaurant.net_spend = round(float(Decimal(str(restaurant.net_spend)) + amount), 2)
        elif bucket == "cancelled":
            cancelled_count += 1
            cancelled += amount
            point.cancelled_spend = round(float(Decimal(str(point.cancelled_spend)) + amount), 2)
            restaurant.cancelled_spend = round(float(Decimal(str(restaurant.cancelled_spend)) + amount), 2)
        else:
            pending_count += 1
            pending += amount
            point.pending_spend = round(float(Decimal(str(point.pending_spend)) + amount), 2)
            restaurant.pending_spend = round(float(Decimal(str(restaurant.pending_spend)) + amount), 2)

    summary = _finalize_summary(
        orders_count=orders_count,
        delivered_orders_count=delivered_count,
        cancelled_orders_count=cancelled_count,
        pending_orders_count=pending_count,
        gross_spend=gross,
        net_spend=net,
        cancelled_spend=cancelled,
        pending_spend=pending,
    )
    return summary, status_counts, daily, restaurant_map


def _build_daily_points_complete(
    rows: list[OrderAnalyticsRow],
    start_date: date,
    end_date: date,
) -> list[AnalyticsDailyPoint]:
    daily = _default_daily_map(start_date, end_date)
    for row in rows:
        point = daily[row.created_at.date()]
        amount = row.total_price
        bucket = _status_bucket(row.status)
        point.orders_count += 1
        point.gross_spend = round(float(Decimal(str(point.gross_spend)) + amount), 2)
        if bucket == "delivered":
            point.net_spend = round(float(Decimal(str(point.net_spend)) + amount), 2)
        elif bucket == "cancelled":
            point.cancelled_spend = round(float(Decimal(str(point.cancelled_spend)) + amount), 2)
        else:
            point.pending_spend = round(float(Decimal(str(point.pending_spend)) + amount), 2)
    return [daily[day] for day in sorted(daily)]


async def build_merchant_analytics(
    session: AsyncSession,
    *,
    restaurant_id: int,
    period: AnalyticsPeriod,
    start_date: date | None = None,
    end_date: date | None = None,
    now: datetime | None = None,
) -> MerchantAnalyticsResponse:
    window = resolve_analytics_range(period, start_date=start_date, end_date=end_date, now=now)
    start_dt = _start_of_day(window.start_date)
    end_dt = _end_of_day(window.end_date)
    order_rows = await _load_order_rows(
        session,
        start_dt=start_dt,
        end_dt=end_dt,
        restaurant_id=restaurant_id,
    )
    item_rows = await _load_item_rows(
        session,
        start_dt=start_dt,
        end_dt=end_dt,
        restaurant_id=restaurant_id,
    )
    summary, _, _, _ = _sum_orders(order_rows)
    daily_sales = _build_daily_points_complete(order_rows, window.start_date, window.end_date)
    status_breakdown = _build_status_breakdown(order_rows)
    item_breakdown = _build_item_breakdown(item_rows, key_getter=lambda row: (row.menu_item_id, row.item_name))
    category_breakdown = _build_item_breakdown(
        item_rows,
        key_getter=lambda row: (row.category_id, row.category_name or "Uncategorized"),
    )
    item_breakdown.sort(key=lambda item: (-item.quantity, -item.net_spend, item.name.lower()))
    return MerchantAnalyticsResponse(
        period=window,
        summary=summary,
        daily_sales=daily_sales,
        status_breakdown=status_breakdown,
        top_selling_items=item_breakdown[:10],
        category_breakdown=category_breakdown[:10],
    )


async def build_customer_analytics(
    session: AsyncSession,
    *,
    customer_id: int,
    period: AnalyticsPeriod,
    start_date: date | None = None,
    end_date: date | None = None,
    now: datetime | None = None,
) -> CustomerAnalyticsResponse:
    user = await session.get(User, customer_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    window = resolve_analytics_range(period, start_date=start_date, end_date=end_date, now=now)
    start_dt = _start_of_day(window.start_date)
    end_dt = _end_of_day(window.end_date)
    order_rows = await _load_order_rows(
        session,
        start_dt=start_dt,
        end_dt=end_dt,
        customer_id=customer_id,
    )
    item_rows = await _load_item_rows(
        session,
        start_dt=start_dt,
        end_dt=end_dt,
        customer_id=customer_id,
    )
    summary, _, _, _ = _sum_orders(order_rows)
    daily_spend = _build_daily_points_complete(order_rows, window.start_date, window.end_date)
    restaurant_breakdown, category_breakdown, food_breakdown = _build_customer_breakdowns(order_rows, item_rows)
    food_breakdown.sort(key=lambda item: (-item.quantity, -item.net_spend, item.name.lower()))

    delivered_points = sum(
        calculate_loyalty_points(row.total_price)
        for row in order_rows
        if _status_bucket(row.status) == "delivered"
    )
    loyalty = _loyalty_summary(user, delivered_points, summary.orders_count, Decimal(str(summary.net_spend)))
    top_ordered_item = food_breakdown[0] if food_breakdown else None

    return CustomerAnalyticsResponse(
        period=window,
        summary=summary,
        loyalty=loyalty,
        daily_spend=daily_spend,
        restaurant_breakdown=restaurant_breakdown[:10],
        category_breakdown=category_breakdown[:10],
        food_breakdown=food_breakdown[:10],
        top_ordered_item=top_ordered_item,
    )


async def apply_completed_order_loyalty(session: AsyncSession, order: Order) -> None:
    if not order.customer_id:
        return

    customer = await session.get(User, order.customer_id)
    if not customer:
        return

    amount = _money(order.total_price)
    points_earned = calculate_loyalty_points(amount)

    customer.total_orders = int(customer.total_orders or 0) + 1
    customer.total_spent = _money(customer.total_spent) + amount
    if points_earned > 0:
        customer.loyalty_points = int(customer.loyalty_points or 0) + points_earned
        customer.loyalty_points_earned = int(customer.loyalty_points_earned or 0) + points_earned
