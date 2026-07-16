from __future__ import annotations
from typing import TYPE_CHECKING
import enum

from sqlalchemy import Boolean, Integer, String, Float, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.restaurants.models import Restaurant
    from app.modules.catalog.models import MenuItem
    from app.modules.customers.models import CustomerAddress


class CartStatus(str, enum.Enum):
    active = "active"
    abandoned = "abandoned"
    checked_out = "checked_out"


class Cart(Base, TimestampMixin):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False)
    address_id: Mapped[int | None] = mapped_column(ForeignKey("customer_addresses.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[CartStatus] = mapped_column(SQLEnum(CartStatus), default=CartStatus.active, nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    coupon_discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    service_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    subtotal_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    needs_cutlery: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cooking_request: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    delivery_instruction: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    restaurant: Mapped["Restaurant"] = relationship(foreign_keys=[restaurant_id])
    address: Mapped["CustomerAddress | None"] = relationship(foreign_keys=[address_id])
    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    modifier_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    add_on_selections: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)

    cart: Mapped[Cart] = relationship(back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship(foreign_keys=[menu_item_id])
