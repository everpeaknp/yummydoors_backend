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
    ReservationStatusUpdateRequest,
    ReservationTableAvailability,
    RestaurantTableCreateRequest,
    RestaurantTableSummary,
    RestaurantTableUpdateRequest,
)
from app.modules.restaurants.models import Restaurant


class ReservationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReservationRepository(db)

    def _can_manage_restaurant(self, user: User, restaurant_id: int) -> bool:
        role_codes = {user_role.role.code for user_role in user.roles}
        if role_codes.intersection({"super_admin", "ops_admin"}):
            return True
        return any(
            assignment.restaurant_id == restaurant_id and assignment.assignment_type == "owner"
            for assignment in user.restaurant_assignments
        )

    async def _require_managed_restaurant(self, user: User, restaurant_id: int) -> Restaurant:
        if not self._can_manage_restaurant(user, restaurant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to manage this restaurant.",
            )
        restaurant = await self.repo.get_restaurant_by_id(restaurant_id)
        if restaurant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
        return restaurant

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
    def _normalize_time(value: str) -> str:
        raw = value.strip().upper()
        for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
            try:
                return datetime.strptime(raw, fmt).strftime("%H:%M")
            except ValueError:
                continue
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation time must be in HH:MM or h:mm AM/PM format.",
        )

    @staticmethod
    def _validate_guest_window(min_guest_count: int, max_guest_count: int) -> None:
        if max_guest_count < min_guest_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Table max guest count cannot be less than min guest count.",
            )

    @staticmethod
    def _serialize_table(table: RestaurantTable | None) -> RestaurantTableSummary | None:
        if table is None:
            return None
        return RestaurantTableSummary(
            id=table.id,
            code=table.code,
            label=table.label,
            zone=table.zone,
            min_guest_count=table.min_guest_count,
            max_guest_count=table.max_guest_count,
            seat_capacity=table.max_guest_count,
            category=table.zone or "Indoor",
            status=table.status,
            sort_order=table.sort_order,
        )

    def _serialize_reservation(self, reservation: TableReservation) -> ReservationResponse:
        restaurant = reservation.restaurant
        selected_table = self._serialize_table(reservation.table)
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
            occasion=reservation.occasion,
            special_request=reservation.special_request,
            cancellation_reason=reservation.cancellation_reason,
            source=reservation.source,
            selected_table=selected_table,
            selected_table_label=selected_table.label if selected_table is not None else None,
            selected_table_zone=selected_table.zone if selected_table is not None else None,
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
        reservation_time: str | None = None,
    ) -> ReservationAvailabilityResponse:
        restaurant = await self.repo.get_restaurant_by_slug(slug)
        if restaurant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
        if not restaurant.supports_table_booking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This restaurant does not support table booking.",
            )

        allowed_slots = self._parse_service_window(restaurant.opening_time, restaurant.closing_time)
        normalized_time = self._normalize_time(reservation_time) if reservation_time is not None else None
        if normalized_time is not None and normalized_time not in allowed_slots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested reservation time is outside the restaurant booking window.",
            )

        active_tables = await self.repo.list_active_tables(restaurant.id)
        eligible_tables = [table for table in active_tables if self._match_capacity(table, guest_count)]
        reservations = await self.repo.list_reservations_for_slot(
            restaurant_id=restaurant.id,
            reservation_date=reservation_date,
        )

        slots: list[ReservationAvailabilitySlot] = []
        for slot in allowed_slots:
            reserved_table_ids = {
                reservation.table_id
                for reservation in reservations
                if reservation.reservation_time == slot and reservation.table_id is not None
            }
            available_tables = [table for table in eligible_tables if table.id not in reserved_table_ids]
            slots.append(
                ReservationAvailabilitySlot(
                    time=slot,
                    is_available=bool(available_tables) or not eligible_tables,
                    remaining_tables=len(available_tables) if eligible_tables else 0,
                    available_table_ids=[table.id for table in available_tables],
                )
            )

        table_inventory: list[ReservationTableAvailability] = []
        if normalized_time is not None:
            reserved_table_ids = {
                reservation.table_id
                for reservation in reservations
                if reservation.reservation_time == normalized_time and reservation.table_id is not None
            }
            table_inventory = [
                ReservationTableAvailability(
                    table=self._serialize_table(table),
                    status="booked" if table.id in reserved_table_ids else "available",
                )
                for table in eligible_tables
            ]

        return ReservationAvailabilityResponse(
            restaurant_id=restaurant.id,
            restaurant_slug=restaurant.slug,
            reservation_date=reservation_date,
            reservation_time=normalized_time,
            guest_count=guest_count,
            available_tables=[self._serialize_table(table) for table in eligible_tables],
            slots=slots,
            table_inventory=table_inventory,
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
        if payload.reservation_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reservation date cannot be in the past.",
            )

        normalized_time = self._normalize_time(payload.reservation_time)
        allowed_slots = self._parse_service_window(restaurant.opening_time, restaurant.closing_time)
        if normalized_time not in allowed_slots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested reservation time is outside the restaurant booking window.",
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
            reservation_time=normalized_time,
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
            status=ReservationStatus.pending,
            reservation_date=payload.reservation_date,
            reservation_time=normalized_time,
            guest_count=payload.guest_count,
            contact_name=payload.contact_name,
            contact_phone=payload.contact_phone,
            contact_email=payload.contact_email,
            occasion=payload.occasion,
            special_request=payload.special_request,
        )
        reservation = await self.repo.create_reservation(reservation)
        await self.repo.add_status_event(
            reservation_id=reservation.id,
            status=ReservationStatus.pending,
            note="Reservation created from customer booking flow.",
        )
        await self.repo.save()
        stored = await self.repo.get_customer_reservation(current_user.id, reservation.id)
        assert stored is not None
        return self._serialize_reservation(stored)

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
        stored = await self.repo.get_customer_reservation(current_user.id, reservation.id)
        assert stored is not None
        return self._serialize_reservation(stored)

    async def list_merchant_tables(self, user: User, restaurant_id: int) -> list[RestaurantTableSummary]:
        await self._require_managed_restaurant(user, restaurant_id)
        tables = await self.repo.list_tables(restaurant_id)
        return [self._serialize_table(table) for table in tables]

    async def create_merchant_table(
        self,
        user: User,
        restaurant_id: int,
        payload: RestaurantTableCreateRequest,
    ) -> RestaurantTableSummary:
        await self._require_managed_restaurant(user, restaurant_id)
        self._validate_guest_window(payload.min_guest_count, payload.max_guest_count)

        existing = await self.repo.list_tables(restaurant_id)
        if any(table.code.lower() == payload.code.lower() for table in existing):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A table with this code already exists for the restaurant.",
            )

        table = RestaurantTable(
            restaurant_id=restaurant_id,
            code=payload.code.strip(),
            label=payload.label.strip(),
            zone=payload.zone.strip() if payload.zone else None,
            min_guest_count=payload.min_guest_count,
            max_guest_count=payload.max_guest_count,
            status=payload.status.strip(),
            sort_order=payload.sort_order,
        )
        stored = await self.repo.create_table(table)
        await self.repo.save()
        return self._serialize_table(stored)

    async def update_merchant_table(
        self,
        user: User,
        restaurant_id: int,
        table_id: int,
        payload: RestaurantTableUpdateRequest,
    ) -> RestaurantTableSummary:
        await self._require_managed_restaurant(user, restaurant_id)
        table = await self.repo.get_table(restaurant_id, table_id)
        if table is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found.")

        data = payload.model_dump(exclude_unset=True)
        next_min = data.get("min_guest_count", table.min_guest_count)
        next_max = data.get("max_guest_count", table.max_guest_count)
        self._validate_guest_window(next_min, next_max)

        if "code" in data and data["code"] is not None:
            next_code = data["code"].strip()
            siblings = await self.repo.list_tables(restaurant_id)
            if any(item.id != table_id and item.code.lower() == next_code.lower() for item in siblings):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A table with this code already exists for the restaurant.",
                )
            table.code = next_code

        if "label" in data and data["label"] is not None:
            table.label = data["label"].strip()
        if "zone" in data:
            table.zone = data["zone"].strip() if data["zone"] else None
        if "min_guest_count" in data:
            table.min_guest_count = data["min_guest_count"]
        if "max_guest_count" in data:
            table.max_guest_count = data["max_guest_count"]
        if "status" in data and data["status"] is not None:
            table.status = data["status"].strip()
        if "sort_order" in data and data["sort_order"] is not None:
            table.sort_order = data["sort_order"]

        await self.repo.save()
        await self.repo.refresh(table)
        return self._serialize_table(table)

    async def delete_merchant_table(self, user: User, restaurant_id: int, table_id: int) -> None:
        await self._require_managed_restaurant(user, restaurant_id)
        table = await self.repo.get_table(restaurant_id, table_id)
        if table is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found.")
        if await self.repo.has_active_reservations_for_table(table_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This table still has active reservations and cannot be deleted.",
            )
        await self.repo.delete_table(table)
        await self.repo.save()

    async def list_merchant_reservations(
        self,
        user: User,
        restaurant_id: int,
        *,
        reservation_date: date | None = None,
        status_filter: ReservationStatus | None = None,
    ) -> list[ReservationResponse]:
        await self._require_managed_restaurant(user, restaurant_id)
        reservations = await self.repo.list_restaurant_reservations(
            restaurant_id=restaurant_id,
            reservation_date=reservation_date,
            status=status_filter,
        )
        return [self._serialize_reservation(item) for item in reservations]

    async def get_merchant_reservation(
        self,
        user: User,
        restaurant_id: int,
        reservation_id: int,
    ) -> ReservationResponse:
        await self._require_managed_restaurant(user, restaurant_id)
        reservation = await self.repo.get_restaurant_reservation(
            restaurant_id=restaurant_id,
            reservation_id=reservation_id,
        )
        if reservation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
        return self._serialize_reservation(reservation)

    async def update_merchant_reservation_status(
        self,
        user: User,
        restaurant_id: int,
        reservation_id: int,
        payload: ReservationStatusUpdateRequest,
    ) -> ReservationResponse:
        await self._require_managed_restaurant(user, restaurant_id)
        reservation = await self.repo.get_restaurant_reservation(
            restaurant_id=restaurant_id,
            reservation_id=reservation_id,
        )
        if reservation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
        if reservation.status in {ReservationStatus.completed, ReservationStatus.cancelled, ReservationStatus.no_show}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reservation can no longer be updated.",
            )

        if payload.table_id is not None:
            selected_table = await self.repo.get_table(restaurant_id, payload.table_id)
            if selected_table is None or selected_table.status != "active":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected table not found.")
            if not self._match_capacity(selected_table, reservation.guest_count):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected table does not match the reservation guest count.",
                )
            slot_reservations = await self.repo.list_reservations_for_slot(
                restaurant_id=restaurant_id,
                reservation_date=reservation.reservation_date,
                reservation_time=reservation.reservation_time,
            )
            conflicting = next(
                (
                    item
                    for item in slot_reservations
                    if item.id != reservation.id and item.table_id == selected_table.id
                ),
                None,
            )
            if conflicting is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Selected table is already booked for this reservation slot.",
                )
            reservation.table_id = selected_table.id

        reservation.status = payload.status
        if payload.status == ReservationStatus.cancelled:
            reservation.cancellation_reason = payload.note or "Cancelled by merchant."

        await self.repo.add_status_event(
            reservation_id=reservation.id,
            status=payload.status,
            note=payload.note,
        )
        await self.repo.save()
        stored = await self.repo.get_restaurant_reservation(
            restaurant_id=restaurant_id,
            reservation_id=reservation_id,
        )
        assert stored is not None
        return self._serialize_reservation(stored)
