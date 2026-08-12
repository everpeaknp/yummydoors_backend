from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User


class RiderSalary(Base, TimestampMixin):
    """Current monthly salary for a platform-tier rider, set by an admin.
    Platform riders are salaried company staff (bikes provided), not
    commission-based gig workers -- there is no per-delivery pay math."""

    __tablename__ = "rider_salaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    monthly_amount: Mapped[float] = mapped_column(Float, nullable=False)
    set_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    rider: Mapped["User"] = relationship(foreign_keys=[rider_user_id])
    set_by: Mapped["User | None"] = relationship(foreign_keys=[set_by_user_id])


class RiderPayrollPayment(Base, TimestampMixin):
    """One row per rider per pay period (e.g. "2026-08"). `amount` snapshots
    the salary at the time this period's row was created, so a later salary
    change doesn't retroactively rewrite an already-pending or paid period.
    """

    __tablename__ = "rider_payroll_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    rider: Mapped["User"] = relationship(foreign_keys=[rider_user_id])
    paid_by: Mapped["User | None"] = relationship(foreign_keys=[paid_by_user_id])

    __table_args__ = (UniqueConstraint("rider_user_id", "period", name="uq_rider_payroll_rider_period"),)
