from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.rider_applications.schemas import RiderApplicationCreateRequest, RiderApplicationReviewRequest, RiderApplicationResponse
from app.modules.rider_applications.service import RiderApplicationService
from app.schemas.common import ApiResponse

router = APIRouter(tags=["Rider Applications"])


@router.get("/rider-applications/me", response_model=ApiResponse[list[RiderApplicationResponse]])
async def list_my_rider_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderApplicationService(db)
    data = await service.list_my_applications(current_user.id)
    return ApiResponse(message="Rider applications fetched successfully.", data=data)


@router.post("/rider-applications", response_model=ApiResponse[RiderApplicationResponse])
async def create_rider_application(
    payload: RiderApplicationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderApplicationService(db)
    data = await service.create_application(current_user=current_user, payload=payload)
    return ApiResponse(message="Rider application created successfully.", data=data)


@router.get(
    "/admin/rider-applications",
    response_model=ApiResponse[list[RiderApplicationResponse]],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_admin_rider_applications(
    db: AsyncSession = Depends(get_db),
):
    service = RiderApplicationService(db)
    data = await service.list_admin_applications()
    return ApiResponse(message="Rider applications fetched successfully.", data=data)


@router.post(
    "/admin/rider-applications/{application_id}/approve",
    response_model=ApiResponse[RiderApplicationResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def approve_rider_application(
    application_id: int,
    payload: RiderApplicationReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderApplicationService(db)
    data = await service.approve_application(
        application_id=application_id,
        admin_user=current_user,
        admin_notes=payload.admin_notes,
    )
    return ApiResponse(message="Rider application approved successfully.", data=data)


@router.post(
    "/admin/rider-applications/{application_id}/reject",
    response_model=ApiResponse[RiderApplicationResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def reject_rider_application(
    application_id: int,
    payload: RiderApplicationReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderApplicationService(db)
    data = await service.reject_application(
        application_id=application_id,
        admin_user=current_user,
        admin_notes=payload.admin_notes,
    )
    return ApiResponse(message="Rider application rejected successfully.", data=data)
