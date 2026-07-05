from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum as SQLEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.restaurants.models import Restaurant


class ReservationStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    seated = "seated"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class RestaurantTable(Base, TimestampMixin):
    __tablename__ = "restaurant_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    min_guest_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_guest_count: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant")

    __table_args__ = (
        UniqueConstraint("restaurant_id", "code", name="uq_restaurant_table_code"),
    )


class TableReservation(Base, TimestampMixin):
    __tablename__ = "table_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurant_tables.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reservation_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        SQLEnum(ReservationStatus), default=ReservationStatus.confirmed, nullable=False
    )
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reservation_time: Mapped[str] = mapped_column(String(10), nullable=False)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    special_request: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="yummydoors", nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    customer: Mapped["User"] = relationship("User")
    restaurant: Mapped["Restaurant"] = relationship("Restaurant")
    table: Mapped[RestaurantTable | None] = relationship("RestaurantTable")
    status_events: Mapped[list["ReservationStatusEvent"]] = relationship(
        back_populates="reservation", cascade="all, delete-orphan"
    )


class ReservationStatusEvent(Base, TimestampMixin):
    __tablename__ = "reservation_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("table_reservations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ReservationStatus] = mapped_column(SQLEnum(ReservationStatus), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    reservation: Mapped[TableReservation] = relationship(back_populates="status_events")
