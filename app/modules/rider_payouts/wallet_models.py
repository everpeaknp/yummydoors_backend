from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User


class RiderWallet(Base, TimestampMixin):
    """One row per freelance/platform rider. Balance is debited
    automatically when a COD delivery's commission can't be collected any
    other way (the rider already has the customer's cash in hand), and
    credited manually by an admin once the rider pays what they owe outside
    the app (WhatsApp -> admin tops up their wallet). Mirrors exactly how
    inDrive's driver wallet works in cash-heavy markets.
    """

    __tablename__ = "rider_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    rider: Mapped["User"] = relationship(foreign_keys=[rider_user_id])


class RiderWalletTransaction(Base, TimestampMixin):
    """Audit trail for every wallet movement — debits from COD commission,
    credits from admin top-ups."""

    __tablename__ = "rider_wallet_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("rider_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    # "debit" (commission owed from a COD delivery) | "credit" (admin top-up)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    wallet: Mapped["RiderWallet"] = relationship(foreign_keys=[wallet_id])
