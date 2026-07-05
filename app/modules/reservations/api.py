from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.reservations.models import ReservationStatus
from app.modules.reservations.schemas import (
    ReservationAvailabilityResponse,
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationResponse,
    ReservationStatusUpdateRequest,
    RestaurantTableCreateRequest,
    RestaurantTableSummary,
    RestaurantTableUpdateRequest,
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
    reservation_time: str | None = Query(default=None, description="Requested booking time."),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.get_availability(
        slug=slug,
        reservation_date=reservation_date,
        guest_count=guest_count,
        reservation_time=reservation_time,
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


@router.get(
    "/merchant/restaurants/{restaurant_id}/reservation-tables",
    response_model=ApiResponse[list[RestaurantTableSummary]],
    summary="List reservation tables for a merchant restaurant",
)
async def list_merchant_reservation_tables(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.list_merchant_tables(current_user, restaurant_id)
    return ApiResponse(message="Reservation tables fetched successfully.", data=data)


@router.post(
    "/merchant/restaurants/{restaurant_id}/reservation-tables",
    response_model=ApiResponse[RestaurantTableSummary],
    status_code=status.HTTP_201_CREATED,
    summary="Create a reservation table for a merchant restaurant",
)
async def create_merchant_reservation_table(
    restaurant_id: int,
    payload: RestaurantTableCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.create_merchant_table(current_user, restaurant_id, payload)
    return ApiResponse(message="Reservation table created successfully.", data=data)


@router.put(
    "/merchant/restaurants/{restaurant_id}/reservation-tables/{table_id}",
    response_model=ApiResponse[RestaurantTableSummary],
    summary="Update a reservation table for a merchant restaurant",
)
async def update_merchant_reservation_table(
    restaurant_id: int,
    table_id: int,
    payload: RestaurantTableUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.update_merchant_table(current_user, restaurant_id, table_id, payload)
    return ApiResponse(message="Reservation table updated successfully.", data=data)


@router.delete(
    "/merchant/restaurants/{restaurant_id}/reservation-tables/{table_id}",
    response_model=ApiResponse[dict],
    summary="Delete a reservation table for a merchant restaurant",
)
async def delete_merchant_reservation_table(
    restaurant_id: int,
    table_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    await service.delete_merchant_table(current_user, restaurant_id, table_id)
    return ApiResponse(message="Reservation table deleted successfully.", data={"success": True})


@router.get(
    "/merchant/restaurants/{restaurant_id}/reservations",
    response_model=ApiResponse[list[ReservationResponse]],
    summary="List reservations for a merchant restaurant",
)
async def list_merchant_reservations(
    restaurant_id: int,
    reservation_date: date | None = Query(default=None),
    status_filter: ReservationStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.list_merchant_reservations(
        current_user,
        restaurant_id,
        reservation_date=reservation_date,
        status_filter=status_filter,
    )
    return ApiResponse(message="Merchant reservations fetched successfully.", data=data)


@router.get(
    "/merchant/restaurants/{restaurant_id}/reservations/{reservation_id}",
    response_model=ApiResponse[ReservationResponse],
    summary="Get reservation detail for a merchant restaurant",
)
async def get_merchant_reservation(
    restaurant_id: int,
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.get_merchant_reservation(current_user, restaurant_id, reservation_id)
    return ApiResponse(message="Merchant reservation fetched successfully.", data=data)


@router.post(
    "/merchant/restaurants/{restaurant_id}/reservations/{reservation_id}/status",
    response_model=ApiResponse[ReservationResponse],
    summary="Update reservation status for a merchant restaurant",
)
async def update_merchant_reservation_status(
    restaurant_id: int,
    reservation_id: int,
    payload: ReservationStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.update_merchant_reservation_status(
        current_user,
        restaurant_id,
        reservation_id,
        payload,
    )
    return ApiResponse(message="Merchant reservation updated successfully.", data=data)
