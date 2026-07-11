from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AnalyticsPeriod(str, Enum):
    today = "today"
    yesterday = "yesterday"
    last_week = "last_week"
    last_7_days = "last_7_days"
    last_month = "last_month"
    last_30_days = "last_30_days"
    this_year = "this_year"
    custom = "custom"


class AnalyticsDateRange(BaseModel):
    period: AnalyticsPeriod
    label: str
    start_date: date
    end_date: date


class AnalyticsSummary(BaseModel):
    orders_count: int = 0
    delivered_orders_count: int = 0
    cancelled_orders_count: int = 0
    pending_orders_count: int = 0
    refunded_orders_count: int = 0
    gross_spend: float = 0.0
    net_spend: float = 0.0
    cancelled_spend: float = 0.0
    pending_spend: float = 0.0
    refunded_spend: float = 0.0
    average_order_value: float = 0.0


class AnalyticsDailyPoint(BaseModel):
    date: date
    orders_count: int = 0
    gross_spend: float = 0.0
    net_spend: float = 0.0
    cancelled_spend: float = 0.0
    pending_spend: float = 0.0
    refunded_spend: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AnalyticsStatusBreakdown(BaseModel):
    status: str
    orders_count: int = 0
    spend: float = 0.0


class AnalyticsBreakdownItem(BaseModel):
    id: int | None = None
    name: str
    orders_count: int = 0
    quantity: int = 0
    gross_spend: float = 0.0
    net_spend: float = 0.0
    cancelled_spend: float = 0.0
    pending_spend: float = 0.0
    refunded_spend: float = 0.0


class AnalyticsLoyaltySummary(BaseModel):
    current_points: int = 0
    total_orders: int = 0
    total_spent: float = 0.0
    lifetime_points_earned: int = 0
    lifetime_points_redeemed: int = 0
    points_earned_in_period: int = 0
    points_rate: float = 0.05


class MerchantAnalyticsResponse(BaseModel):
    period: AnalyticsDateRange
    summary: AnalyticsSummary
    daily_sales: list[AnalyticsDailyPoint] = []
    status_breakdown: list[AnalyticsStatusBreakdown] = []
    top_selling_items: list[AnalyticsBreakdownItem] = []
    category_breakdown: list[AnalyticsBreakdownItem] = []


class CustomerAnalyticsResponse(BaseModel):
    period: AnalyticsDateRange
    summary: AnalyticsSummary
    loyalty: AnalyticsLoyaltySummary
    daily_spend: list[AnalyticsDailyPoint] = []
    restaurant_breakdown: list[AnalyticsBreakdownItem] = []
    category_breakdown: list[AnalyticsBreakdownItem] = []
    food_breakdown: list[AnalyticsBreakdownItem] = []
    top_ordered_item: AnalyticsBreakdownItem | None = None
