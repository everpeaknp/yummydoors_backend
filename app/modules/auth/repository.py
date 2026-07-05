from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import (
    AuthAuditLog,
    AuthRateLimit,
    PasswordResetCode,
    RefreshSession,
    Role,
    User,
    UserRole,
)
from app.modules.integrations.pos.models import ExternalUserLink
from app.modules.restaurants.models import RestaurantUserAssignment
from app.modules.workspaces.models import Workspace, WorkspaceMembership


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions),
                selectinload(User.restaurant_assignments).selectinload(
                    RestaurantUserAssignment.restaurant
                ),
                selectinload(User.external_links),
                selectinload(User.active_workspace).selectinload(Workspace.primary_restaurant),
                selectinload(User.workspace_memberships)
                .selectinload(WorkspaceMembership.workspace)
                .selectinload(Workspace.primary_restaurant),
            )
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_user_by_phone(self, phone: str) -> User | None:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_user_for_login(self, identifier: str) -> User | None:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions),
                selectinload(User.restaurant_assignments),
                selectinload(User.external_links),
                selectinload(User.active_workspace).selectinload(Workspace.primary_restaurant),
                selectinload(User.workspace_memberships)
                .selectinload(WorkspaceMembership.workspace)
                .selectinload(Workspace.primary_restaurant),
            )
            .where(or_(User.email == identifier.lower(), User.phone == identifier))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_identifier(self, identifier: str) -> User | None:
        result = await self.db.execute(
            select(User).where(or_(User.email == identifier.lower(), User.phone == identifier))
        )
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user

    async def create_external_user_link(self, link: ExternalUserLink) -> ExternalUserLink:
        self.db.add(link)
        await self.db.flush()
        return link

    async def get_role_by_code(self, code: str) -> Role | None:
        result = await self.db.execute(select(Role).where(Role.code == code))
        return result.scalar_one_or_none()

    async def add_user_role(
        self,
        user_id: int,
        role_id: int,
        restaurant_id: int | None = None,
        branch_id: int | None = None,
    ) -> UserRole:
        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
        )
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def create_refresh_session(self, session: RefreshSession) -> RefreshSession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def revoke_all_refresh_sessions_for_user(self, user_id: int) -> None:
        result = await self.db.execute(
            select(RefreshSession).where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
        )
        for session in result.scalars():
            session.revoked_at = datetime.now(UTC)
            session.is_current = False
        await self.db.flush()

    async def get_refresh_session(self, token_jti: str) -> RefreshSession | None:
        result = await self.db.execute(select(RefreshSession).where(RefreshSession.token_jti == token_jti))
        return result.scalar_one_or_none()

    async def revoke_refresh_session(self, session: RefreshSession) -> None:
        session.revoked_at = datetime.now(UTC)
        session.is_current = False
        await self.db.flush()

    async def create_password_reset_code(self, reset_code: PasswordResetCode) -> PasswordResetCode:
        self.db.add(reset_code)
        await self.db.flush()
        return reset_code

    async def expire_password_reset_codes_for_user(self, user_id: int) -> None:
        result = await self.db.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == user_id,
                PasswordResetCode.used.is_(False),
            )
        )
        now = datetime.now(UTC)
        for code in result.scalars():
            code.used = True
            if code.expires_at > now:
                code.expires_at = now
        await self.db.flush()

    async def get_valid_password_reset_code(
        self,
        *,
        user_id: int,
        code: str,
    ) -> PasswordResetCode | None:
        result = await self.db.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.user_id == user_id,
                PasswordResetCode.code == code,
                PasswordResetCode.used.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_external_user_link(self, *, system_name: str, external_user_id: str) -> ExternalUserLink | None:
        result = await self.db.execute(
            select(ExternalUserLink).where(
                ExternalUserLink.system_name == system_name,
                ExternalUserLink.external_user_id == external_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_rate_limit(self, *, action: str, key: str) -> AuthRateLimit | None:
        result = await self.db.execute(
            select(AuthRateLimit).where(
                AuthRateLimit.action == action,
                AuthRateLimit.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def create_rate_limit(self, record: AuthRateLimit) -> AuthRateLimit:
        self.db.add(record)
        await self.db.flush()
        return record

    async def create_audit_log(self, log: AuthAuditLog) -> AuthAuditLog:
        self.db.add(log)
        await self.db.flush()
        return log

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def find_pos_link_candidates(self, email: str | None, phone: str | None) -> list[dict]:
        candidates: list[dict] = []
        if email:
            candidates.append({"match_type": "email", "identifier": email, "system_name": "yummy_pos"})
        return candidates
