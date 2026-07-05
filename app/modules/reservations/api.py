from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.reservations.schemas import (
    ReservationAvailabilityResponse,
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationResponse,
)
from app.modules.reservations.service import ReservationService
from app.schemas.common import ApiResponse

router = APIRouter(tags=["Reservations"])


@router.get(
    "/restaurants/{slug}/reservations/availability",
    response_model=ApiResponse[ReservationAvailabilityResponse],
    summary="Get public table-booking availability for a restaurant",
)
async def get_reservation_availability(
    slug: str,
    reservation_date: date = Query(..., description="Requested booking date."),
    guest_count: int | None = Query(default=None, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.get_availability(
        slug=slug,
        reservation_date=reservation_date,
        guest_count=guest_count,
    )
    return ApiResponse(message="Reservation availability fetched successfully.", data=data)


@router.post(
    "/restaurants/{slug}/reservations",
    response_model=ApiResponse[ReservationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer table reservation",
)
async def create_reservation(
    slug: str,
    payload: ReservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.create_reservation(slug=slug, current_user=current_user, payload=payload)
    return ApiResponse(message="Reservation created successfully.", data=data)


@router.get(
    "/reservations",
    response_model=ApiResponse[list[ReservationResponse]],
    summary="List my reservations",
)
async def list_my_reservations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.list_my_reservations(current_user)
    return ApiResponse(message="Reservations fetched successfully.", data=data)


@router.get(
    "/reservations/{reservation_id}",
    response_model=ApiResponse[ReservationResponse],
    summary="Get my reservation detail",
)
async def get_my_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.get_my_reservation(current_user, reservation_id)
    return ApiResponse(message="Reservation fetched successfully.", data=data)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ApiResponse[ReservationResponse],
    summary="Cancel my reservation",
)
async def cancel_my_reservation(
    reservation_id: int,
    payload: ReservationCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.cancel_my_reservation(
        current_user=current_user,
        reservation_id=reservation_id,
        payload=payload,
    )
    return ApiResponse(message="Reservation cancelled successfully.", data=data)
