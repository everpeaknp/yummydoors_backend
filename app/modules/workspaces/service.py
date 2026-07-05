from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.restaurants.models import Restaurant, RestaurantUserAssignment
from app.modules.workspaces.models import (
    MerchantApplication,
    MerchantRestaurantRequest,
    Workspace,
    WorkspaceMembership,
)
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.schemas import (
    MerchantApplicationCreateRequest,
    MerchantApplicationResponse,
    MerchantRestaurantListResponse,
    MerchantRestaurantSummary,
    MerchantRestaurantSwitchRequest,
    MerchantApplicationUpdateRequest,
    MerchantRestaurantRequestCreate,
    MerchantRestaurantRequestResponse,
    WorkspaceListResponse,
    WorkspaceSummary,
)


class WorkspaceService:
    def __init__(self, session: AsyncSession):
        self.repository = WorkspaceRepository(session)

    async def ensure_customer_workspace(self, user: User) -> Workspace:
        workspace = await self.repository.get_or_create_customer_workspace(user)
        if user.active_workspace_id is None:
            user.active_workspace_id = workspace.id
        return workspace

    async def list_user_workspaces(self, user_id: int) -> WorkspaceListResponse:
        user = await self.repository.get_user_with_workspaces(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        await self.ensure_customer_workspace(user)
        self._ensure_active_restaurant(user)
        await self.repository.commit()
        refreshed = await self.repository.get_user_with_workspaces(user_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="User not found.")
        return self._build_workspace_list_response(refreshed)

    async def switch_workspace(self, *, user_id: int, workspace_id: int) -> WorkspaceListResponse:
        user = await self.repository.get_user_with_workspaces(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        membership = await self.repository.get_workspace_membership(user_id=user_id, workspace_id=workspace_id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This workspace is not available for the current user.",
            )

        user.active_workspace_id = membership.workspace_id
        if membership.workspace.primary_restaurant_id is not None:
            user.active_restaurant_id = membership.workspace.primary_restaurant_id
        await self.repository.commit()
        refreshed = await self.repository.get_user_with_workspaces(user_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="User not found.")
        return self._build_workspace_list_response(refreshed)

    async def list_my_merchant_restaurants(self, user_id: int) -> MerchantRestaurantListResponse:
        user = await self.repository.get_user_with_workspaces(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        self._ensure_active_restaurant(user)
        await self.repository.commit()
        refreshed = await self.repository.get_user_with_workspaces(user_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="User not found.")
        return self._build_merchant_restaurant_list_response(refreshed)

    async def switch_active_restaurant(
        self,
        *,
        user_id: int,
        payload: MerchantRestaurantSwitchRequest,
    ) -> MerchantRestaurantListResponse:
        user = await self.repository.get_user_with_workspaces(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        restaurant_map = self._collect_merchant_restaurants(user)
        if payload.restaurant_id not in restaurant_map:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This restaurant is not available for the current user.",
            )

        user.active_restaurant_id = payload.restaurant_id
        await self.repository.commit()
        refreshed = await self.repository.get_user_with_workspaces(user_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="User not found.")
        return self._build_merchant_restaurant_list_response(refreshed)

    async def create_merchant_application(
        self,
        *,
        user: User,
        payload: MerchantApplicationCreateRequest,
    ) -> MerchantApplicationResponse:
        hydrated_user = await self.repository.get_user_with_workspaces(user.id)
        if hydrated_user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        await self.ensure_customer_workspace(hydrated_user)

        existing_applications = await self.repository.list_user_applications(hydrated_user.id)
        
        # Conflict only if they have a submitted application pending review
        submitted_application = next(
            (application for application in existing_applications if application.status == "submitted"),
            None,
        )
        if submitted_application is not None:
            raise HTTPException(
                status_code=409,
                detail="You already have a submitted application pending review. Please wait for approval.",
            )
            
        # Automatically clean up abandoned drafts if the user restarts the wizard
        for app in existing_applications:
            if app.status == "draft":
                await self.repository.session.delete(app)
                
        await self.repository.session.flush()

        merchant_workspace = next(
            (
                membership.workspace
                for membership in hydrated_user.workspace_memberships
                if membership.workspace.workspace_type == "merchant"
            ),
            None,
        )
        if merchant_workspace is None:
            merchant_workspace = Workspace(
                workspace_type="merchant",
                name=payload.business_name.strip(),
                slug=await self._build_unique_workspace_slug(payload.business_name),
                status="pending",
                is_personal=False,
                metadata_json={"created_by_user_id": hydrated_user.id},
            )
            await self.repository.create_workspace(merchant_workspace)
            await self.repository.create_membership(
                WorkspaceMembership(
                    workspace_id=merchant_workspace.id,
                    user_id=hydrated_user.id,
                    membership_role="owner",
                    status="active",
                    is_primary=False,
                )
            )
        elif merchant_workspace.name != payload.business_name.strip():
            merchant_workspace.name = payload.business_name.strip()

        application = MerchantApplication(
            user_id=hydrated_user.id,
            workspace_id=merchant_workspace.id,
            status="draft",
            business_name=payload.business_name.strip(),
            contact_name=payload.contact_name.strip(),
            contact_email=payload.contact_email.lower() if payload.contact_email else None,
            contact_phone=payload.contact_phone,
            notes=payload.notes,
        )
        await self.repository.create_merchant_application(application)
        await self.repository.commit()

        stored = await self.repository.get_application_for_user(
            application_id=application.id,
            user_id=hydrated_user.id,
        )
        if stored is None:
            raise HTTPException(status_code=500, detail="Merchant application creation failed.")
        return self._build_application_response(stored)

    async def update_merchant_application(
        self,
        *,
        user_id: int,
        application_id: int,
        payload: MerchantApplicationUpdateRequest,
    ) -> MerchantApplicationResponse:
        application = await self.repository.get_application_for_user(application_id=application_id, user_id=user_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        if application.status not in {"draft", "rejected"}:
            raise HTTPException(status_code=409, detail="Only draft or rejected applications can be edited.")

        data = payload.model_dump(exclude_unset=True)
        if "contact_email" in data and data["contact_email"] is not None:
            data["contact_email"] = data["contact_email"].lower()
        for key, value in data.items():
            setattr(application, key, value.strip() if isinstance(value, str) else value)

        await self.repository.commit()
        refreshed = await self.repository.get_application_for_user(application_id=application_id, user_id=user_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        return self._build_application_response(refreshed)

    async def add_restaurant_request(
        self,
        *,
        user_id: int,
        application_id: int,
        payload: MerchantRestaurantRequestCreate,
    ) -> MerchantApplicationResponse:
        application = await self.repository.get_application_for_user(application_id=application_id, user_id=user_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        if application.status not in {"draft", "rejected"}:
            raise HTTPException(status_code=409, detail="Restaurant requests can only be changed while draft.")

        linked_restaurant = None
        if payload.restaurant_id is not None:
            linked_restaurant = await self.repository.get_restaurant_by_id(payload.restaurant_id)
            if linked_restaurant is None:
                raise HTTPException(status_code=404, detail="Referenced restaurant was not found.")

        request = MerchantRestaurantRequest(
            application_id=application.id,
            request_type=payload.request_type,
            status="draft",
            restaurant_id=payload.restaurant_id,
            requested_name=payload.requested_name.strip(),
            requested_slug=payload.requested_slug.strip() if payload.requested_slug else None,
            city=payload.city,
            area=payload.area,
            latitude=payload.latitude,
            longitude=payload.longitude,
            source_system="yummy_pos" if payload.request_type == "pos_link" else "yummydoors",
            pos_restaurant_id=payload.pos_restaurant_id,
            notes=payload.notes,
            metadata_json={"linked_restaurant_name": linked_restaurant.name if linked_restaurant else None},
        )
        await self.repository.create_merchant_restaurant_request(request)
        await self.repository.commit()

        refreshed = await self.repository.get_application_for_user(application_id=application_id, user_id=user_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        return self._build_application_response(refreshed)

    async def list_my_merchant_applications(self, user_id: int) -> list[MerchantApplicationResponse]:
        applications = await self.repository.list_user_applications(user_id)
        return [self._build_application_response(application) for application in applications]

    async def get_my_merchant_application(
        self,
        *,
        user_id: int,
        application_id: int,
    ) -> MerchantApplicationResponse:
        application = await self.repository.get_application_for_user(application_id=application_id, user_id=user_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        return self._build_application_response(application)

    async def submit_merchant_application(
        self,
        *,
        user_id: int,
        application_id: int,
    ) -> MerchantApplicationResponse:
        application = await self.repository.get_application_for_user(application_id=application_id, user_id=user_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        if application.status not in {"draft", "rejected"}:
            raise HTTPException(status_code=409, detail="This merchant application is not editable.")
        if not application.restaurant_requests:
            raise HTTPException(status_code=400, detail="Add at least one restaurant request before submitting.")

        application.status = "submitted"
        if application.workspace is not None and application.workspace.status != "active":
            application.workspace.status = "pending_review"
        for request in application.restaurant_requests:
            request.status = "submitted"
        await self.repository.commit()

        refreshed = await self.repository.get_application_for_user(application_id=application_id, user_id=user_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        return self._build_application_response(refreshed)

    async def list_admin_applications(self) -> list[MerchantApplicationResponse]:
        applications = await self.repository.list_all_applications()
        return [self._build_application_response(application) for application in applications]

    async def approve_application(
        self,
        *,
        application_id: int,
        admin_notes: str | None,
    ) -> MerchantApplicationResponse:
        application = await self.repository.get_application_by_id(application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        if application.status != "submitted":
            raise HTTPException(status_code=409, detail="Only submitted applications can be approved.")

        owner_role = await self.repository.get_role_by_code("restaurant_owner")
        if owner_role is None:
            raise HTTPException(status_code=500, detail="Restaurant owner role is missing.")

        primary_restaurant: Restaurant | None = None
        for request in application.restaurant_requests:
            if request.request_type == "create_external":
                restaurant = Restaurant(
                    name=request.requested_name,
                    slug=await self._build_unique_restaurant_slug(request.requested_slug or request.requested_name),
                    integration_mode="external",
                    status="active",
                    city=request.city,
                    area=request.area,
                    short_description=f"Merchant onboarded via {application.business_name}",
                )
                await self.repository.create_restaurant(restaurant)
                request.restaurant_id = restaurant.id
                primary_restaurant = primary_restaurant or restaurant
            elif request.restaurant_id is not None:
                restaurant = await self.repository.get_restaurant_by_id(request.restaurant_id)
                if restaurant is None:
                    raise HTTPException(status_code=404, detail="Referenced restaurant no longer exists.")
                primary_restaurant = primary_restaurant or restaurant
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Non-external restaurant requests must reference an existing restaurant.",
                )

            request.status = "approved"
            if request.restaurant_id is not None:
                existing_assignment = await self.repository.get_restaurant_assignment(
                    user_id=application.user_id,
                    restaurant_id=request.restaurant_id,
                    assignment_type="owner",
                )
                if existing_assignment is None:
                    await self.repository.create_restaurant_assignment(
                        RestaurantUserAssignment(
                            user_id=application.user_id,
                            restaurant_id=request.restaurant_id,
                            branch_id=None,
                            assignment_type="owner",
                            source_system=request.source_system,
                            external_role_snapshot="merchant_application_approved",
                        )
                    )
                existing_user_role = await self.repository.get_user_role(
                    user_id=application.user_id,
                    role_id=owner_role.id,
                    restaurant_id=request.restaurant_id,
                    branch_id=None,
                )
                if existing_user_role is None:
                    await self.repository.add_user_role(
                        user_id=application.user_id,
                        role_id=owner_role.id,
                        restaurant_id=request.restaurant_id,
                        branch_id=None,
                    )

        application.status = "approved"
        application.admin_notes = admin_notes
        if application.workspace is not None:
            application.workspace.status = "active"
            if primary_restaurant is not None:
                application.workspace.primary_restaurant_id = primary_restaurant.id
                user = await self.repository.get_user_with_workspaces(application.user_id)
                if user is not None and user.active_restaurant_id is None:
                    user.active_restaurant_id = primary_restaurant.id
        await self.repository.commit()

        refreshed = await self.repository.get_application_by_id(application_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        return self._build_application_response(refreshed)

    async def reject_application(
        self,
        *,
        application_id: int,
        admin_notes: str | None,
    ) -> MerchantApplicationResponse:
        application = await self.repository.get_application_by_id(application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        if application.status not in {"submitted", "draft"}:
            raise HTTPException(status_code=409, detail="This application cannot be rejected now.")

        application.status = "rejected"
        application.admin_notes = admin_notes
        if application.workspace is not None and application.workspace.status != "active":
            application.workspace.status = "rejected"
        for request in application.restaurant_requests:
            if request.status == "submitted":
                request.status = "rejected"
        await self.repository.commit()

        refreshed = await self.repository.get_application_by_id(application_id)
        if refreshed is None:
            raise HTTPException(status_code=404, detail="Merchant application not found.")
        return self._build_application_response(refreshed)

    def _build_workspace_summary(self, membership: WorkspaceMembership) -> WorkspaceSummary:
        workspace = membership.workspace
        return WorkspaceSummary(
            id=workspace.id,
            workspace_type=workspace.workspace_type,
            name=workspace.name,
            slug=workspace.slug,
            status=workspace.status,
            membership_role=membership.membership_role,
            is_primary=membership.is_primary,
            primary_restaurant_id=workspace.primary_restaurant_id,
            primary_restaurant_name=workspace.primary_restaurant.name if workspace.primary_restaurant else None,
        )

    def _build_workspace_list_response(self, user: User) -> WorkspaceListResponse:
        memberships = sorted(
            user.workspace_memberships,
            key=lambda item: (item.workspace.workspace_type, item.workspace.id),
        )
        summaries = [self._build_workspace_summary(item) for item in memberships if item.status == "active"]
        active_workspace = next((item for item in summaries if item.id == user.active_workspace_id), None)
        return WorkspaceListResponse(
            active_workspace_id=user.active_workspace_id,
            active_workspace=active_workspace,
            available_workspaces=summaries,
        )

    def _collect_merchant_restaurants(self, user: User) -> dict[int, dict]:
        restaurant_map: dict[int, dict] = {}
        for assignment in user.restaurant_assignments:
            restaurant = assignment.restaurant
            if restaurant is None:
                continue
            record = restaurant_map.setdefault(
                restaurant.id,
                {
                    "restaurant": restaurant,
                    "ownership_types": set(),
                },
            )
            record["ownership_types"].add(assignment.assignment_type)
        return restaurant_map

    def _ensure_active_restaurant(self, user: User) -> None:
        restaurant_map = self._collect_merchant_restaurants(user)
        if not restaurant_map:
            user.active_restaurant_id = None
            return
        if user.active_restaurant_id in restaurant_map:
            return
        if user.active_workspace and user.active_workspace.primary_restaurant_id in restaurant_map:
            user.active_restaurant_id = user.active_workspace.primary_restaurant_id
            return
        user.active_restaurant_id = next(iter(sorted(restaurant_map.keys())))

    def _build_merchant_restaurant_list_response(self, user: User) -> MerchantRestaurantListResponse:
        restaurant_map = self._collect_merchant_restaurants(user)
        items = []
        for restaurant_id in sorted(restaurant_map.keys()):
            record = restaurant_map[restaurant_id]
            restaurant = record["restaurant"]
            ownership_types = sorted(record["ownership_types"])
            items.append(
                MerchantRestaurantSummary(
                    id=restaurant.id,
                    name=restaurant.name,
                    slug=restaurant.slug,
                    city=restaurant.city,
                    area=restaurant.area,
                    integration_mode=restaurant.integration_mode,
                    status=restaurant.status,
                    logo_url=restaurant.logo_url,
                    cover_image_url=restaurant.cover_image_url,
                    primary_cuisine_label=restaurant.primary_cuisine_label,
                    is_active_context=user.active_restaurant_id == restaurant.id,
                    ownership_types=ownership_types,
                )
            )
        return MerchantRestaurantListResponse(
            active_restaurant_id=user.active_restaurant_id,
            items=items,
        )

    def _build_restaurant_request_response(
        self,
        request: MerchantRestaurantRequest,
    ) -> MerchantRestaurantRequestResponse:
        return MerchantRestaurantRequestResponse(
            id=request.id,
            request_type=request.request_type,
            status=request.status,
            restaurant_id=request.restaurant_id,
            requested_name=request.requested_name,
            requested_slug=request.requested_slug,
            city=request.city,
            area=request.area,
            latitude=request.latitude,
            longitude=request.longitude,
            source_system=request.source_system,
            pos_restaurant_id=request.pos_restaurant_id,
            notes=request.notes,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )

    def _build_application_response(self, application: MerchantApplication) -> MerchantApplicationResponse:
        workspace_summary = None
        if application.workspace is not None:
            workspace_summary = WorkspaceSummary(
                id=application.workspace.id,
                workspace_type=application.workspace.workspace_type,
                name=application.workspace.name,
                slug=application.workspace.slug,
                status=application.workspace.status,
                membership_role="owner",
                is_primary=False,
                primary_restaurant_id=application.workspace.primary_restaurant_id,
                primary_restaurant_name=(
                    application.workspace.primary_restaurant.name
                    if application.workspace.primary_restaurant
                    else None
                ),
            )
        return MerchantApplicationResponse(
            id=application.id,
            user_id=application.user_id,
            workspace_id=application.workspace_id,
            workspace=workspace_summary,
            status=application.status,
            business_name=application.business_name,
            contact_name=application.contact_name,
            contact_email=application.contact_email,
            contact_phone=application.contact_phone,
            notes=application.notes,
            admin_notes=application.admin_notes,
            restaurant_requests=[
                self._build_restaurant_request_response(request)
                for request in application.restaurant_requests
            ],
            created_at=application.created_at,
            updated_at=application.updated_at,
        )

    async def _build_unique_workspace_slug(self, value: str) -> str:
        return await self._build_unique_slug(value, lookup=self.repository.get_workspace_by_slug)

    async def _build_unique_restaurant_slug(self, value: str) -> str:
        return await self._build_unique_slug(value, lookup=self.repository.get_restaurant_by_slug)

    async def _build_unique_slug(self, value: str, *, lookup) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "workspace"
        candidate = slug
        counter = 2
        while await lookup(candidate) is not None:
            candidate = f"{slug}-{counter}"
            counter += 1
        return candidate
