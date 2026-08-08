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


class RestaurantSettlement(Base, TimestampMixin):
    """One row per delivered order recording the platform's commission
    claim on that order — direction depends on how the customer paid:

    - COD ("cash"): the merchant/rider collected the full cash from the
      customer, so the merchant now OWES the platform the commission
      (direction="collect_from_merchant"). Matches how Pathao actually
      settles COD orders — merchant keeps the cash, platform invoices them
      for the commission afterward.
    - Online (e.g. "esewa"): the platform already holds the customer's
      payment, so the platform OWES the merchant their share
      (direction="pay_to_merchant").

    Snapshots subtotal/rate/commission at computation time so a later rate
    change doesn't retroactively rewrite historical settlements.
    """

    __tablename__ = "restaurant_settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(24), nullable=False)
    subtotal_amount: Mapped[float] = mapped_column(Float, nullable=False)
    commission_rate_percent: Mapped[float] = mapped_column(Float, nullable=False)
    commission_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    order: Mapped["Order"] = relationship(foreign_keys=[order_id])
    restaurant: Mapped["Restaurant"] = relationship(foreign_keys=[restaurant_id])
    settled_by: Mapped["User | None"] = relationship(foreign_keys=[settled_by_user_id])
