from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.analytics.service import (
    ItemAnalyticsRow,
    OrderAnalyticsRow,
    _build_customer_breakdowns,
    apply_completed_order_loyalty,
    calculate_loyalty_points,
    resolve_analytics_range,
)
from app.modules.analytics.schemas import AnalyticsPeriod
from app.modules.orders.models import OrderStatus


class _Session:
    def __init__(self, user):
        self.user = user
        self.requested_ids: list[int] = []

    async def get(self, model, obj_id):
        self.requested_ids.append(obj_id)
        return self.user


def test_resolve_analytics_range_supports_calendar_and_rolling_windows():
    now = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)

    yesterday = resolve_analytics_range(AnalyticsPeriod.yesterday, now=now)
    assert yesterday.start_date == date(2026, 7, 10)
    assert yesterday.end_date == date(2026, 7, 10)

    last_week = resolve_analytics_range(AnalyticsPeriod.last_week, now=now)
    assert last_week.start_date == date(2026, 6, 29)
    assert last_week.end_date == date(2026, 7, 5)

    last_month = resolve_analytics_range(AnalyticsPeriod.last_month, now=now)
    assert last_month.start_date == date(2026, 6, 1)
    assert last_month.end_date == date(2026, 6, 30)

    custom = resolve_analytics_range(
        AnalyticsPeriod.custom,
        start_date=date(2026, 1, 3),
        end_date=date(2026, 1, 9),
        now=now,
    )
    assert custom.start_date == date(2026, 1, 3)
    assert custom.end_date == date(2026, 1, 9)


def test_calculate_loyalty_points_floors_per_order_amount():
    assert calculate_loyalty_points(100) == 5
    assert calculate_loyalty_points(199.99) == 9


@pytest.mark.asyncio
async def test_apply_completed_order_loyalty_updates_user_counters():
    user = SimpleNamespace(
        id=7,
        total_orders=2,
        total_spent=Decimal("250.00"),
        loyalty_points=12,
        loyalty_points_earned=12,
        loyalty_points_redeemed=3,
    )
    session = _Session(user)
    order = SimpleNamespace(customer_id=7, total_price=Decimal("199.99"))

    await apply_completed_order_loyalty(session, order)

    assert session.requested_ids == [7]
    assert user.total_orders == 3
    assert user.total_spent == Decimal("449.99")
    assert user.loyalty_points == 21
    assert user.loyalty_points_earned == 21
    assert user.loyalty_points_redeemed == 3


def test_customer_breakdowns_group_restaurants_categories_and_foods():
    order_rows = [
        OrderAnalyticsRow(
            order_id=1,
            restaurant_id=10,
            restaurant_name="Alpha",
            status=OrderStatus.delivered,
            total_price=Decimal("100.00"),
            subtotal_amount=Decimal("80.00"),
            created_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
        ),
        OrderAnalyticsRow(
            order_id=2,
            restaurant_id=20,
            restaurant_name="Beta",
            status=OrderStatus.cancelled,
            total_price=Decimal("50.00"),
            subtotal_amount=Decimal("50.00"),
            created_at=datetime(2026, 7, 10, 10, 0, tzinfo=UTC),
        ),
    ]
    item_rows = [
        ItemAnalyticsRow(
            order_id=1,
            restaurant_id=10,
            restaurant_name="Alpha",
            status=OrderStatus.delivered,
            order_total=Decimal("100.00"),
            order_subtotal=Decimal("80.00"),
            created_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
            menu_item_id=1,
            item_name="Margherita Pizza",
            category_id=100,
            category_name="Pizza",
            quantity=2,
            unit_price=Decimal("40.00"),
        ),
        ItemAnalyticsRow(
            order_id=2,
            restaurant_id=20,
            restaurant_name="Beta",
            status=OrderStatus.cancelled,
            order_total=Decimal("50.00"),
            order_subtotal=Decimal("50.00"),
            created_at=datetime(2026, 7, 10, 10, 0, tzinfo=UTC),
            menu_item_id=2,
            item_name="Classic Burger",
            category_id=200,
            category_name="Burger",
            quantity=1,
            unit_price=Decimal("50.00"),
        ),
    ]

    restaurant_breakdown, category_breakdown, food_breakdown = _build_customer_breakdowns(
        order_rows,
        item_rows,
    )

    assert restaurant_breakdown[0].name == "Alpha"
    assert restaurant_breakdown[0].net_spend == 100.0
    assert restaurant_breakdown[1].name == "Beta"
    assert restaurant_breakdown[1].cancelled_spend == 50.0
    assert category_breakdown[0].name == "Pizza"
    assert category_breakdown[0].net_spend == 100.0
    assert food_breakdown[0].name == "Margherita Pizza"
    assert food_breakdown[0].quantity == 2
