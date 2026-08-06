from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin


class PromotionDiscountType(str, enum.Enum):
    percentage = "percentage"
    fixed = "fixed"
    free_delivery = "free_delivery"


class Promotion(Base, TimestampMixin):
    """A coupon/promotion code, replacing the previous hardcoded
    WELCOME50/SAVE10/FREEDEL string comparisons scattered across the cart and
    order-summary code paths."""

    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    discount_type: Mapped[PromotionDiscountType] = mapped_column(
        default=PromotionDiscountType.fixed, nullable=False
    )
    discount_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_discount_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_order_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    restaurant_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    per_user_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    restaurant = relationship("Restaurant")


class PromotionRedemption(Base, TimestampMixin):
    """One row per successful use of a promotion on a placed order."""

    __tablename__ = "promotion_redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    promotion = relationship("Promotion")
