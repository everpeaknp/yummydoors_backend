from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import Role, User, UserRole
from app.modules.restaurants.models import Restaurant, RestaurantUserAssignment
from app.modules.workspaces.models import (
    MerchantApplication,
    MerchantRestaurantRequest,
    Workspace,
    WorkspaceMembership,
)


class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_workspace(self, user_id: int) -> "Workspace | None":
        """Return the user's currently-active workspace (with primary_restaurant loaded)."""
        from app.modules.workspaces.models import Workspace as _Workspace
        stmt = (
            select(User)
            .options(
                selectinload(User.active_workspace).selectinload(_Workspace.primary_restaurant),
            )
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return user.active_workspace

    async def get_user_with_workspaces(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(
                selectinload(User.active_workspace).selectinload(Workspace.primary_restaurant),
                selectinload(User.workspace_memberships)
                .selectinload(WorkspaceMembership.workspace)
                .selectinload(Workspace.primary_restaurant),
                selectinload(User.roles).selectinload(UserRole.role),
                selectinload(User.restaurant_assignments).selectinload(RestaurantUserAssignment.restaurant),
                selectinload(User.external_links),
            )
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_workspace_membership(self, *, user_id: int, workspace_id: int) -> WorkspaceMembership | None:
        stmt = (
            select(WorkspaceMembership)
            .options(selectinload(WorkspaceMembership.workspace).selectinload(Workspace.primary_restaurant))
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.status == "active",
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_code(self, code: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.code == code))
        return result.scalar_one_or_none()

    async def create_workspace(self, workspace: Workspace) -> Workspace:
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def create_membership(self, membership: WorkspaceMembership) -> WorkspaceMembership:
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def get_workspace_by_slug(self, slug: str) -> Workspace | None:
        result = await self.session.execute(select(Workspace).where(Workspace.slug == slug))
        return result.scalar_one_or_none()

    async def get_workspace_by_name_and_type(self, *, user_id: int, name: str, workspace_type: str) -> Workspace | None:
        stmt = (
            select(Workspace)
            .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(
                WorkspaceMembership.user_id == user_id,
                Workspace.workspace_type == workspace_type,
                Workspace.name == name,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_customer_workspace(self, user: User) -> Workspace:
        stmt = (
            select(WorkspaceMembership)
            .options(selectinload(WorkspaceMembership.workspace))
            .where(
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.membership_role == "owner",
                WorkspaceMembership.status == "active",
            )
        )
        result = await self.session.execute(stmt)
        memberships = result.scalars().all()
        for membership in memberships:
            if membership.workspace.workspace_type == "customer":
                return membership.workspace

        workspace = Workspace(
            workspace_type="customer",
            name=f"{user.full_name.strip()} Customer",
            slug=None,
            status="active",
            is_personal=True,
            metadata_json={"owner_user_id": user.id},
        )
        self.session.add(workspace)
        await self.session.flush()

        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=user.id,
            membership_role="owner",
            status="active",
            is_primary=True,
        )
        self.session.add(membership)
        await self.session.flush()
        return workspace

    async def create_merchant_application(self, application: MerchantApplication) -> MerchantApplication:
        self.session.add(application)
        await self.session.flush()
        return application

    async def create_merchant_restaurant_request(
        self,
        request: MerchantRestaurantRequest,
    ) -> MerchantRestaurantRequest:
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_application_for_user(self, *, application_id: int, user_id: int) -> MerchantApplication | None:
        stmt = (
            select(MerchantApplication)
            .options(
                selectinload(MerchantApplication.workspace).selectinload(Workspace.primary_restaurant),
                selectinload(MerchantApplication.restaurant_requests),
            )
            .where(MerchantApplication.id == application_id, MerchantApplication.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_application_by_id(self, application_id: int) -> MerchantApplication | None:
        stmt = (
            select(MerchantApplication)
            .options(
                selectinload(MerchantApplication.workspace).selectinload(Workspace.primary_restaurant),
                selectinload(MerchantApplication.restaurant_requests),
            )
            .where(MerchantApplication.id == application_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_user_applications(self, user_id: int) -> list[MerchantApplication]:
        stmt = (
            select(MerchantApplication)
            .options(
                selectinload(MerchantApplication.workspace).selectinload(Workspace.primary_restaurant),
                selectinload(MerchantApplication.restaurant_requests),
            )
            .where(MerchantApplication.user_id == user_id)
            .order_by(MerchantApplication.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_applications(self) -> list[MerchantApplication]:
        stmt = (
            select(MerchantApplication)
            .options(
                selectinload(MerchantApplication.workspace).selectinload(Workspace.primary_restaurant),
                selectinload(MerchantApplication.restaurant_requests),
            )
            .order_by(MerchantApplication.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_restaurant_by_id(self, restaurant_id: int) -> Restaurant | None:
        result = await self.session.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
        return result.scalar_one_or_none()

    async def get_restaurant_by_slug(self, slug: str) -> Restaurant | None:
        result = await self.session.execute(select(Restaurant).where(Restaurant.slug == slug))
        return result.scalar_one_or_none()

    async def create_restaurant(self, restaurant: Restaurant) -> Restaurant:
        self.session.add(restaurant)
        await self.session.flush()
        return restaurant

    async def create_restaurant_assignment(
        self,
        assignment: RestaurantUserAssignment,
    ) -> RestaurantUserAssignment:
        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def get_restaurant_assignment(
        self,
        *,
        user_id: int,
        restaurant_id: int,
        assignment_type: str,
    ) -> RestaurantUserAssignment | None:
        stmt = select(RestaurantUserAssignment).where(
            RestaurantUserAssignment.user_id == user_id,
            RestaurantUserAssignment.restaurant_id == restaurant_id,
            RestaurantUserAssignment.assignment_type == assignment_type,
        )
        result = await self.session.execute(stmt)
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

    async def get_user_role(
        self,
        *,
        user_id: int,
        role_id: int,
        restaurant_id: int | None,
        branch_id: int | None,
    ) -> UserRole | None:
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.restaurant_id == restaurant_id,
            UserRole.branch_id == branch_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
