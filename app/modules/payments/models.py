from __future__ import annotations
from typing import TYPE_CHECKING
import enum
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.orders.models import Order


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    failed = "failed"
    refunded = "refunded"


class Payment(Base, TimestampMixin):
    """A single payment attempt/record against an order.

    This is intentionally scoped to what's needed to make payment status a
    real, server-verified fact instead of a client-asserted string: one row
    per payment attempt, with the provider's own reference id and raw
    response kept for audit/dispute purposes. It is not a full accounting
    ledger (no refund workflow, no payout/settlement modeling) — see
    docs/YUMMYDOORS_SYSTEM_STATUS_2026-07-14.md section 12 for what's still
    out of scope.
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), default="NPR", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus), default=PaymentStatus.pending, nullable=False
    )
    raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship(foreign_keys=[order_id])
