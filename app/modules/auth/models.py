from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin
from app.modules.integrations.pos.models import ExternalUserLink

if TYPE_CHECKING:
    from app.modules.integrations.pos.models import ExternalUserLink
    from app.modules.restaurants.models import RestaurantUserAssignment
    from app.modules.workspaces.models import MerchantApplication, Workspace, WorkspaceMembership
    from app.modules.rider_applications.models import RiderApplication

from app.modules.customers.models import CustomerAddress
from app.modules.rider_applications.models import RiderApplication


class UserStatus(StrEnum):
    pending = "pending"
    active = "active"
    suspended = "suspended"
    deleted = "deleted"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=UserStatus.pending, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loyalty_points_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loyalty_points_redeemed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_location_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    default_address_id: Mapped[int | None] = mapped_column(ForeignKey("customer_addresses.id", ondelete="SET NULL", use_alter=True), nullable=True)
    active_restaurant_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurants.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    active_workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    roles: Mapped[list[UserRole]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_sessions: Mapped[list[RefreshSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_codes: Mapped[list[PasswordResetCode]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    external_links: Mapped[list[ExternalUserLink]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    restaurant_assignments: Mapped[list[RestaurantUserAssignment]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    addresses: Mapped[list["CustomerAddress"]] = relationship(
        "CustomerAddress",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys=[CustomerAddress.user_id],
    )
    workspace_memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    active_workspace: Mapped["Workspace | None"] = relationship(
        "Workspace",
        foreign_keys=[active_workspace_id],
    )
    merchant_applications: Mapped[list["MerchantApplication"]] = relationship(
        "MerchantApplication",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    rider_applications: Mapped[list["RiderApplication"]] = relationship(
        "RiderApplication",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys=[RiderApplication.user_id],
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone", name="uq_users_phone"),
    )


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), default="global", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    permissions: Mapped[list[RolePermission]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    users: Mapped[list[UserRole]] = relationship(back_populates="role", cascade="all, delete-orphan")


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list[RolePermission]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship(back_populates="roles")


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    restaurant_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=True
    )
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurant_branches.id", ondelete="CASCADE"), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="roles")
    role: Mapped[Role] = relationship(back_populates="users")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "role_id", "restaurant_id", "branch_id", name="uq_user_role_scope"
        ),
    )


class RefreshSession(Base, TimestampMixin):
    __tablename__ = "refresh_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="refresh_sessions")


class PasswordResetCode(Base, TimestampMixin):
    __tablename__ = "password_reset_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="password_reset_codes")


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("action", "key", name="uq_auth_rate_limit_action_key"),)


class AuthAuditLog(Base, TimestampMixin):
    __tablename__ = "auth_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
