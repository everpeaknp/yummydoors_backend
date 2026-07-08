from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.restaurants.models import Category, Restaurant


class FoodType(str, enum.Enum):
    veg = "veg"
    non_veg = "non_veg"
    vegan = "vegan"


class MenuItem(Base, TimestampMixin):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(10), default="NPR", nullable=False)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    food_type: Mapped[FoodType | None] = mapped_column(SQLEnum(FoodType), nullable=True)
    is_spicy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    popularity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rating_average: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    restaurant: Mapped["Restaurant"] = relationship(foreign_keys=[restaurant_id])
    category: Mapped["Category"] = relationship(foreign_keys=[category_id])
    modifier_groups: Mapped[list["MenuModifierGroup"]] = relationship(
        back_populates="menu_item", cascade="all, delete-orphan"
    )


class MenuModifierGroup(Base):
    __tablename__ = "menu_modifier_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_selections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_selections: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    menu_item: Mapped[MenuItem] = relationship(back_populates="modifier_groups")
    items: Mapped[list["MenuModifierItem"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class MenuModifierItem(Base):
    __tablename__ = "menu_modifier_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("menu_modifier_groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_adjustment: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    group: Mapped[MenuModifierGroup] = relationship(back_populates="items")
