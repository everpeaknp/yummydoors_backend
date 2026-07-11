from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import Role, User, UserRole
from app.modules.rider_applications.models import RiderApplication


class RiderApplicationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_application(self, application: RiderApplication) -> RiderApplication:
        self.session.add(application)
        await self.session.flush()
        return application

    async def get_application_by_id(self, application_id: int) -> RiderApplication | None:
        result = await self.session.execute(
            select(RiderApplication)
            .options(
                selectinload(RiderApplication.user).selectinload(User.roles).selectinload(UserRole.role),
                selectinload(RiderApplication.reviewed_by_user),
            )
            .where(RiderApplication.id == application_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_application_for_user(self, user_id: int) -> RiderApplication | None:
        result = await self.session.execute(
            select(RiderApplication)
            .options(
                selectinload(RiderApplication.user).selectinload(User.roles).selectinload(UserRole.role),
                selectinload(RiderApplication.reviewed_by_user),
            )
            .where(RiderApplication.user_id == user_id)
            .order_by(RiderApplication.id.desc())
        )
        return result.scalars().first()

    async def list_user_applications(self, user_id: int) -> list[RiderApplication]:
        result = await self.session.execute(
            select(RiderApplication)
            .options(
                selectinload(RiderApplication.user).selectinload(User.roles).selectinload(UserRole.role),
                selectinload(RiderApplication.reviewed_by_user),
            )
            .where(RiderApplication.user_id == user_id)
            .order_by(RiderApplication.id.desc())
        )
        return list(result.scalars().all())

    async def list_all_applications(self) -> list[RiderApplication]:
        result = await self.session.execute(
            select(RiderApplication)
            .options(
                selectinload(RiderApplication.user).selectinload(User.roles).selectinload(UserRole.role),
                selectinload(RiderApplication.reviewed_by_user),
            )
            .order_by(RiderApplication.id.desc())
        )
        return list(result.scalars().all())

    async def list_users_by_role_codes(self, role_codes: list[str]) -> list[User]:
        if not role_codes:
            return []
        result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.code.in_(role_codes),
                User.is_active.is_(True),
            )
            .distinct()
        )
        return list(result.scalars().all())

    async def get_role_by_code(self, code: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.code == code))
        return result.scalar_one_or_none()

    async def add_user_role(
        self,
        *,
        user_id: int,
        role_id: int,
        restaurant_id: int | None = None,
        branch_id: int | None = None,
    ) -> UserRole:
        record = UserRole(
            user_id=user_id,
            role_id=role_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def commit(self) -> None:
        await self.session.commit()
