from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.orders.models import Order
    from app.modules.restaurants.models import Restaurant


class RestaurantRiderInvitation(Base, TimestampMixin):
    __tablename__ = "restaurant_rider_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inviter_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invited_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    invited_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    invitation_type: Mapped[str] = mapped_column(String(32), default="private", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    responded_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    restaurant: Mapped["Restaurant"] = relationship()


class OrderDispatchOffer(Base, TimestampMixin):
    __tablename__ = "order_dispatch_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rank_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    responded_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship()
    restaurant: Mapped["Restaurant"] = relationship()

    __table_args__ = (
        UniqueConstraint("order_id", "rider_user_id", "round_number", name="uq_order_dispatch_offer_round"),
    )
