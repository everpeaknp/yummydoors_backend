from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin


class ExternalUserLink(Base, TimestampMixin):
    __tablename__ = "external_user_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    system_name: Mapped[str] = mapped_column(String(50), nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    external_role_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_restaurant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    match_source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="external_links")

    __table_args__ = (
        UniqueConstraint("system_name", "external_user_id", name="uq_external_user_link"),
    )


class RestaurantPosLink(Base, TimestampMixin):
    __tablename__ = "restaurant_pos_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurant_branches.id", ondelete="CASCADE"), nullable=True
    )
    pos_restaurant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    pos_branch_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sync_mode: Mapped[str] = mapped_column(String(32), default="partner", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    restaurant = relationship("Restaurant", back_populates="pos_links")

    __table_args__ = (
        UniqueConstraint("restaurant_id", "pos_restaurant_id", name="uq_restaurant_pos_link"),
    )
