from __future__ import annotations

from datetime import date

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.reservations.models import ReservationStatus, ReservationStatusEvent, RestaurantTable, TableReservation
from app.modules.restaurants.models import Restaurant


class ReservationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_restaurant_by_slug(self, slug: str) -> Restaurant | None:
        result = await self.db.execute(
            select(Restaurant).where(Restaurant.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_active_tables(self, restaurant_id: int) -> list[RestaurantTable]:
        result = await self.db.execute(
            select(RestaurantTable)
            .where(
                RestaurantTable.restaurant_id == restaurant_id,
                RestaurantTable.status == "active",
            )
            .order_by(RestaurantTable.sort_order.asc(), RestaurantTable.id.asc())
        )
        return list(result.scalars().all())

    async def get_table(self, restaurant_id: int, table_id: int) -> RestaurantTable | None:
        result = await self.db.execute(
            select(RestaurantTable).where(
                RestaurantTable.id == table_id,
                RestaurantTable.restaurant_id == restaurant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_reservations_for_slot(
        self,
        *,
        restaurant_id: int,
        reservation_date: date,
        reservation_time: str | None = None,
    ) -> list[TableReservation]:
        conditions = [
            TableReservation.restaurant_id == restaurant_id,
            TableReservation.reservation_date == reservation_date,
            TableReservation.status.in_(
                [ReservationStatus.pending, ReservationStatus.confirmed, ReservationStatus.seated]
            ),
        ]
        if reservation_time is not None:
            conditions.append(TableReservation.reservation_time == reservation_time)

        result = await self.db.execute(
            select(TableReservation)
            .where(and_(*conditions))
            .options(selectinload(TableReservation.table), selectinload(TableReservation.status_events))
        )
        return list(result.scalars().all())

    async def create_reservation(self, reservation: TableReservation) -> TableReservation:
        self.db.add(reservation)
        await self.db.flush()
        await self.db.refresh(reservation)
        return reservation

    async def add_status_event(
        self,
        *,
        reservation_id: int,
        status: ReservationStatus,
        note: str | None = None,
    ) -> ReservationStatusEvent:
        event = ReservationStatusEvent(reservation_id=reservation_id, status=status, note=note)
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_customer_reservations(self, customer_id: int) -> list[TableReservation]:
        result = await self.db.execute(
            select(TableReservation)
            .where(TableReservation.customer_id == customer_id)
            .options(
                selectinload(TableReservation.table),
                selectinload(TableReservation.status_events),
                selectinload(TableReservation.restaurant),
            )
            .order_by(TableReservation.reservation_date.desc(), TableReservation.reservation_time.desc())
        )
        return list(result.scalars().all())

    async def get_customer_reservation(self, customer_id: int, reservation_id: int) -> TableReservation | None:
        result = await self.db.execute(
            select(TableReservation)
            .where(
                TableReservation.id == reservation_id,
                TableReservation.customer_id == customer_id,
            )
            .options(
                selectinload(TableReservation.table),
                selectinload(TableReservation.status_events),
                selectinload(TableReservation.restaurant),
            )
        )
        return result.scalar_one_or_none()

    async def save(self) -> None:
        await self.db.commit()

