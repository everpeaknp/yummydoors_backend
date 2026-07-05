from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.restaurants.models import Restaurant


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    primary_restaurant_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    merchant_applications: Mapped[list["MerchantApplication"]] = relationship(
        back_populates="workspace",
    )
    primary_restaurant: Mapped["Restaurant | None"] = relationship("Restaurant")


class WorkspaceMembership(Base, TimestampMixin):
    __tablename__ = "workspace_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    membership_role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="workspace_memberships")

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )


class MerchantApplication(Base, TimestampMixin):
    __tablename__ = "merchant_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    user: Mapped["User"] = relationship(back_populates="merchant_applications")
    workspace: Mapped["Workspace | None"] = relationship(back_populates="merchant_applications")
    restaurant_requests: Mapped[list["MerchantRestaurantRequest"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )


class MerchantRestaurantRequest(Base, TimestampMixin):
    __tablename__ = "merchant_restaurant_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("merchant_applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(String(32), default="create_external", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    restaurant_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    source_system: Mapped[str] = mapped_column(String(50), default="yummydoors", nullable=False)
    pos_restaurant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    application: Mapped[MerchantApplication] = relationship(back_populates="restaurant_requests")
    restaurant: Mapped["Restaurant | None"] = relationship("Restaurant")
