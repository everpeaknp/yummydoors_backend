from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.catalog.models import MenuItem
    from app.modules.restaurants.models import Restaurant


class UserFavoriteRestaurant(Base, TimestampMixin):
    __tablename__ = "user_favorite_restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    restaurant: Mapped["Restaurant"] = relationship(foreign_keys=[restaurant_id])

    __table_args__ = (
        UniqueConstraint("user_id", "restaurant_id", name="uq_user_favorite_restaurant"),
    )


class UserFavoriteMenuItem(Base, TimestampMixin):
    __tablename__ = "user_favorite_menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    menu_item: Mapped["MenuItem"] = relationship(foreign_keys=[menu_item_id])

    __table_args__ = (
        UniqueConstraint("user_id", "menu_item_id", name="uq_user_favorite_menu_item"),
    )
