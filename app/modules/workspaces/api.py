from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.workspaces.schemas import (
    MerchantApplicationCreateRequest,
    MerchantApplicationResponse,
    MerchantRestaurantListResponse,
    MerchantRestaurantSwitchRequest,
    MerchantApplicationReviewRequest,
    MerchantApplicationUpdateRequest,
    MerchantRestaurantRequestCreate,
    WorkspaceListResponse,
    WorkspaceSwitchRequest,
)
from app.modules.workspaces.service import WorkspaceService
from app.schemas.common import ApiResponse

router = APIRouter(tags=["Workspaces"])


@router.get("/workspaces/me", response_model=ApiResponse[WorkspaceListResponse])
async def list_my_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.list_user_workspaces(current_user.id)
    return ApiResponse(message="User workspaces fetched successfully.", data=data)


@router.post("/workspaces/switch", response_model=ApiResponse[WorkspaceListResponse])
async def switch_workspace(
    payload: WorkspaceSwitchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.switch_workspace(user_id=current_user.id, workspace_id=payload.workspace_id)
    return ApiResponse(message="Workspace switched successfully.", data=data)


@router.get("/merchant/applications/me", response_model=ApiResponse[list[MerchantApplicationResponse]])
async def list_my_merchant_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.list_my_merchant_applications(current_user.id)
    return ApiResponse(message="Merchant applications fetched successfully.", data=data)


@router.get("/merchant/restaurants/me", response_model=ApiResponse[MerchantRestaurantListResponse])
async def list_my_merchant_restaurants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.list_my_merchant_restaurants(current_user.id)
    return ApiResponse(message="Merchant restaurants fetched successfully.", data=data)


@router.post("/merchant/restaurants/switch", response_model=ApiResponse[MerchantRestaurantListResponse])
async def switch_my_active_restaurant(
    payload: MerchantRestaurantSwitchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.switch_active_restaurant(user_id=current_user.id, payload=payload)
    return ApiResponse(message="Active restaurant switched successfully.", data=data)


@router.post("/merchant/applications", response_model=ApiResponse[MerchantApplicationResponse])
async def create_merchant_application(
    payload: MerchantApplicationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.create_merchant_application(user=current_user, payload=payload)
    return ApiResponse(message="Merchant application created successfully.", data=data)


@router.get("/merchant/applications/{application_id}", response_model=ApiResponse[MerchantApplicationResponse])
async def get_my_merchant_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.get_my_merchant_application(user_id=current_user.id, application_id=application_id)
    return ApiResponse(message="Merchant application fetched successfully.", data=data)


@router.patch("/merchant/applications/{application_id}", response_model=ApiResponse[MerchantApplicationResponse])
async def update_merchant_application(
    application_id: int,
    payload: MerchantApplicationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.update_merchant_application(
        user_id=current_user.id,
        application_id=application_id,
        payload=payload,
    )
    return ApiResponse(message="Merchant application updated successfully.", data=data)


@router.post(
    "/merchant/applications/{application_id}/restaurant-requests",
    response_model=ApiResponse[MerchantApplicationResponse],
)
async def add_merchant_restaurant_request(
    application_id: int,
    payload: MerchantRestaurantRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.add_restaurant_request(
        user_id=current_user.id,
        application_id=application_id,
        payload=payload,
    )
    return ApiResponse(message="Restaurant request added successfully.", data=data)


@router.post("/merchant/applications/{application_id}/submit", response_model=ApiResponse[MerchantApplicationResponse])
async def submit_merchant_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.submit_merchant_application(user_id=current_user.id, application_id=application_id)
    return ApiResponse(message="Merchant application submitted successfully.", data=data)


@router.get(
    "/admin/merchant-applications",
    response_model=ApiResponse[list[MerchantApplicationResponse]],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_admin_merchant_applications(
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.list_admin_applications()
    return ApiResponse(message="Merchant applications fetched successfully.", data=data)


@router.post(
    "/admin/merchant-applications/{application_id}/approve",
    response_model=ApiResponse[MerchantApplicationResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def approve_merchant_application(
    application_id: int,
    payload: MerchantApplicationReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.approve_application(application_id=application_id, admin_notes=payload.admin_notes)
    return ApiResponse(message="Merchant application approved successfully.", data=data)


@router.post(
    "/admin/merchant-applications/{application_id}/reject",
    response_model=ApiResponse[MerchantApplicationResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def reject_merchant_application(
    application_id: int,
    payload: MerchantApplicationReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    service = WorkspaceService(db)
    data = await service.reject_application(application_id=application_id, admin_notes=payload.admin_notes)
    return ApiResponse(message="Merchant application rejected successfully.", data=data)
