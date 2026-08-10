from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.orders.models import Order


class RiderReview(Base, TimestampMixin):
    """One review per delivered order, left by the customer for the rider
    who delivered it. Unlike restaurant reviews, this is order-scoped and
    validated server-side (order must be delivered, reviewer must be the
    order's customer, one review per order) since it's a trust signal tied
    to a specific interaction, not a free-standing public comment.
    """

    __tablename__ = "rider_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    rider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    order: Mapped["Order"] = relationship(foreign_keys=[order_id])
    rider: Mapped["User"] = relationship(foreign_keys=[rider_user_id])
    customer: Mapped["User"] = relationship(foreign_keys=[customer_user_id])

    __table_args__ = (UniqueConstraint("order_id", name="uq_rider_reviews_order"),)
