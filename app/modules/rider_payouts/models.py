from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.orders.models import Order
    from app.modules.restaurants.models import Restaurant


class RiderPayout(Base, TimestampMixin):
    """One row per delivered order for a public/freelance (or platform)
    rider — private restaurant-employed riders are paid directly by the
    restaurant and never get a row here. Snapshots the fare inputs
    (distance, rate, commission %) at computation time so a later change to
    the platform's rates doesn't retroactively rewrite historical payouts.
    """

    __tablename__ = "rider_payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    rider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    base_fare: Mapped[float] = mapped_column(Float, nullable=False)
    distance_fare: Mapped[float] = mapped_column(Float, nullable=False)
    gross_fare: Mapped[float] = mapped_column(Float, nullable=False)
    commission_rate_percent: Mapped[float] = mapped_column(Float, nullable=False)
    commission_amount: Mapped[float] = mapped_column(Float, nullable=False)
    payout_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    order: Mapped["Order"] = relationship(foreign_keys=[order_id])
    rider: Mapped["User"] = relationship(foreign_keys=[rider_user_id])
    restaurant: Mapped["Restaurant"] = relationship(foreign_keys=[restaurant_id])
