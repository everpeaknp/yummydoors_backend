from __future__ import annotations
from typing import TYPE_CHECKING
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.restaurants.models import Restaurant
    from app.modules.catalog.models import MenuItem
    from app.modules.customers.models import CustomerAddress


class OrderStatus(str, enum.Enum):
    placed = "placed"
    preparing = "preparing"
    cancelled = "cancelled"
    delivered = "delivered"
    toPay = "toPay"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False)
    address_id: Mapped[int | None] = mapped_column(ForeignKey("customer_addresses.id", ondelete="SET NULL"), nullable=True)
    rider_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.placed, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_address_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    delivery_recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    coupon_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    coupon_discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    service_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    subtotal_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    needs_cutlery: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cooking_request: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    delivery_instruction: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    estimated_delivery_window: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rider_assignment_state: Mapped[str] = mapped_column(String(32), default="unassigned", nullable=False)
    rider_assignment_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rider_assignment_round: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rider_offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preparing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rider_assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    restaurant: Mapped["Restaurant"] = relationship(foreign_keys=[restaurant_id])
    address: Mapped["CustomerAddress | None"] = relationship(foreign_keys=[address_id])
    rider: Mapped["User | None"] = relationship(foreign_keys=[rider_user_id])
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id: Mapped[int | None] = mapped_column(ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True)
    
    # Snapshot of item at time of order
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
