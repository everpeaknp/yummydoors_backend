from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.integrations.pos.models import RestaurantPosLink


class Restaurant(Base, TimestampMixin):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    integration_mode: Mapped[str] = mapped_column(String(32), default="external", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_cuisine_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_average: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    supports_delivery: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_free_delivery: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_pickup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_table_booking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    offer_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    closing_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    about_text: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    facilities_text: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    delivery_eta_min_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_eta_max_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    branches: Mapped[list[RestaurantBranch]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    pos_links: Mapped[list[RestaurantPosLink]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    user_assignments: Mapped[list[RestaurantUserAssignment]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    category_links: Mapped[list[RestaurantCategory]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["RestaurantReview"]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )


class RestaurantBranch(Base, TimestampMixin):
    __tablename__ = "restaurant_branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="branches")
    user_assignments: Mapped[list[RestaurantUserAssignment]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )


class RestaurantUserAssignment(Base, TimestampMixin):
    __tablename__ = "restaurant_user_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurant_branches.id", ondelete="CASCADE"), nullable=True
    )
    assignment_type: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="yummydoors", nullable=False)
    external_role_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped[User] = relationship(back_populates="restaurant_assignments")
    restaurant: Mapped[Restaurant] = relationship(back_populates="user_assignments")
    branch: Mapped[RestaurantBranch] = relationship(back_populates="user_assignments")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "restaurant_id", "branch_id", "assignment_type", name="uq_restaurant_assignment"
        ),
    )


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    restaurant_links: Mapped[list[RestaurantCategory]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class RestaurantCategory(Base):
    __tablename__ = "restaurant_categories"

    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="category_links")
    category: Mapped[Category] = relationship(back_populates="restaurant_links")


class RestaurantReview(Base, TimestampMixin):
    __tablename__ = "restaurant_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    merchant_reply: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="yummydoors", nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="reviews")
    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "restaurant_id", name="uq_restaurant_reviews_user_restaurant"),
    )
