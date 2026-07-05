from __future__ import annotations

from datetime import date, datetime, timedelta
from secrets import token_hex

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.reservations.models import ReservationStatus, RestaurantTable, TableReservation
from app.modules.reservations.repository import ReservationRepository
from app.modules.reservations.schemas import (
    ReservationAvailabilityResponse,
    ReservationAvailabilitySlot,
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationResponse,
    ReservationStatusEventResponse,
    RestaurantTableSummary,
)


class ReservationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReservationRepository(db)

    @staticmethod
    def _parse_service_window(opening_time: str | None, closing_time: str | None) -> list[str]:
        start_raw = opening_time or "10:00"
        end_raw = closing_time or "21:00"
        try:
            start_dt = datetime.strptime(start_raw, "%H:%M")
            end_dt = datetime.strptime(end_raw, "%H:%M")
        except ValueError:
            start_dt = datetime.strptime("10:00", "%H:%M")
            end_dt = datetime.strptime("21:00", "%H:%M")

        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=12)

        slots: list[str] = []
        current = start_dt
        while current < end_dt:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(hours=1)
        return slots

    @staticmethod
    def _match_capacity(table: RestaurantTable, guest_count: int | None) -> bool:
        if guest_count is None:
            return True
        return table.min_guest_count <= guest_count <= table.max_guest_count

    @staticmethod
    def _build_reservation_code() -> str:
        return f"RSV-{token_hex(4).upper()}"

    @staticmethod
    def _serialize_table(table: RestaurantTable | None) -> RestaurantTableSummary | None:
        if table is None:
            return None
        return RestaurantTableSummary.model_validate(table)

    def _serialize_reservation(self, reservation: TableReservation) -> ReservationResponse:
        restaurant = reservation.restaurant
        return ReservationResponse(
            id=reservation.id,
            reservation_code=reservation.reservation_code,
            status=reservation.status.value,
            restaurant_id=reservation.restaurant_id,
            restaurant_name=restaurant.name,
            restaurant_slug=restaurant.slug,
            restaurant_logo_url=restaurant.logo_url,
            reservation_date=reservation.reservation_date,
            reservation_time=reservation.reservation_time,
            guest_count=reservation.guest_count,
            contact_name=reservation.contact_name,
            contact_phone=reservation.contact_phone,
            contact_email=reservation.contact_email,
            special_request=reservation.special_request,
            selected_table=self._serialize_table(reservation.table),
            created_at=reservation.created_at.isoformat(),
            updated_at=reservation.updated_at.isoformat(),
            status_events=[
                ReservationStatusEventResponse(
                    status=event.status.value,
                    note=event.note,
                    created_at=event.created_at.isoformat(),
                )
                for event in sorted(reservation.status_events, key=lambda item: item.created_at)
            ],
        )

    async def get_availability(
        self,
        *,
        slug: str,
        reservation_date: date,
        guest_count: int | None,
    ) -> ReservationAvailabilityResponse:
        restaurant = await self.repo.get_restaurant_by_slug(slug)
        if restaurant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
        if not restaurant.supports_table_booking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This restaurant does not support table booking.",
            )

        active_tables = await self.repo.list_active_tables(restaurant.id)
        eligible_tables = [table for table in active_tables if self._match_capacity(table, guest_count)]
        reservations = await self.repo.list_reservations_for_slot(
            restaurant_id=restaurant.id,
            reservation_date=reservation_date,
        )

        slots: list[ReservationAvailabilitySlot] = []
        for slot in self._parse_service_window(restaurant.opening_time, restaurant.closing_time):
            reserved_table_ids = {
                reservation.table_id
                for reservation in reservations
                if reservation.reservation_time == slot and reservation.table_id is not None
            }
            available_tables = [
                table for table in eligible_tables if table.id not in reserved_table_ids
            ]
            slots.append(
                ReservationAvailabilitySlot(
                    time=slot,
                    is_available=bool(available_tables) or not eligible_tables,
                    remaining_tables=len(available_tables) if eligible_tables else 0,
                    available_table_ids=[table.id for table in available_tables],
                )
            )

        return ReservationAvailabilityResponse(
            restaurant_id=restaurant.id,
            restaurant_slug=restaurant.slug,
            reservation_date=reservation_date,
            guest_count=guest_count,
            available_tables=[RestaurantTableSummary.model_validate(table) for table in eligible_tables],
            slots=slots,
        )

    async def create_reservation(
        self,
        *,
        slug: str,
        current_user: User,
        payload: ReservationCreateRequest,
    ) -> ReservationResponse:
        restaurant = await self.repo.get_restaurant_by_slug(slug)
        if restaurant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
        if not restaurant.supports_table_booking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This restaurant does not support table booking.",
            )

        selected_table = None
        if payload.table_id is not None:
            selected_table = await self.repo.get_table(restaurant.id, payload.table_id)
            if selected_table is None or selected_table.status != "active":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected table not found.")
            if not self._match_capacity(selected_table, payload.guest_count):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected table does not match the requested guest count.",
                )

        existing = await self.repo.list_reservations_for_slot(
            restaurant_id=restaurant.id,
            reservation_date=payload.reservation_date,
            reservation_time=payload.reservation_time,
        )
        reserved_table_ids = {
            reservation.table_id for reservation in existing if reservation.table_id is not None
        }

        if selected_table is None:
            candidate_tables = [
                table
                for table in await self.repo.list_active_tables(restaurant.id)
                if self._match_capacity(table, payload.guest_count) and table.id not in reserved_table_ids
            ]
            if candidate_tables:
                selected_table = candidate_tables[0]
        elif selected_table.id in reserved_table_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected table is no longer available for that time slot.",
            )

        reservation = TableReservation(
            customer_id=current_user.id,
            restaurant_id=restaurant.id,
            table_id=selected_table.id if selected_table is not None else None,
            reservation_code=self._build_reservation_code(),
            status=ReservationStatus.confirmed,
            reservation_date=payload.reservation_date,
            reservation_time=payload.reservation_time,
            guest_count=payload.guest_count,
            contact_name=payload.contact_name,
            contact_phone=payload.contact_phone,
            contact_email=payload.contact_email,
            special_request=payload.special_request,
        )
        reservation = await self.repo.create_reservation(reservation)
        await self.repo.add_status_event(
            reservation_id=reservation.id,
            status=ReservationStatus.confirmed,
            note="Reservation created from customer booking flow.",
        )
        await self.repo.save()
        reservation = await self.repo.get_customer_reservation(current_user.id, reservation.id)
        assert reservation is not None
        return self._serialize_reservation(reservation)

    async def list_my_reservations(self, current_user: User) -> list[ReservationResponse]:
        reservations = await self.repo.list_customer_reservations(current_user.id)
        return [self._serialize_reservation(item) for item in reservations]

    async def get_my_reservation(self, current_user: User, reservation_id: int) -> ReservationResponse:
        reservation = await self.repo.get_customer_reservation(current_user.id, reservation_id)
        if reservation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
        return self._serialize_reservation(reservation)

    async def cancel_my_reservation(
        self,
        *,
        current_user: User,
        reservation_id: int,
        payload: ReservationCancelRequest,
    ) -> ReservationResponse:
        reservation = await self.repo.get_customer_reservation(current_user.id, reservation_id)
        if reservation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
        if reservation.status in {ReservationStatus.cancelled, ReservationStatus.completed, ReservationStatus.no_show}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reservation can no longer be cancelled.",
            )

        reservation.status = ReservationStatus.cancelled
        reservation.cancellation_reason = payload.reason
        await self.repo.add_status_event(
            reservation_id=reservation.id,
            status=ReservationStatus.cancelled,
            note=payload.reason or "Cancelled by customer.",
        )
        await self.repo.save()
        reservation = await self.repo.get_customer_reservation(current_user.id, reservation.id)
        assert reservation is not None
        return self._serialize_reservation(reservation)
