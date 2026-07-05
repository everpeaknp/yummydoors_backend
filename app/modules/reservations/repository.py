from __future__ import annotations

from datetime import date

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.reservations.models import (
    ReservationStatus,
    ReservationStatusEvent,
    RestaurantTable,
    TableReservation,
)
from app.modules.restaurants.models import Restaurant


class ReservationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_restaurant_by_slug(self, slug: str) -> Restaurant | None:
        result = await self.db.execute(select(Restaurant).where(Restaurant.slug == slug))
        return result.scalar_one_or_none()

    async def get_restaurant_by_id(self, restaurant_id: int) -> Restaurant | None:
        result = await self.db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
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

    async def list_tables(self, restaurant_id: int) -> list[RestaurantTable]:
        result = await self.db.execute(
            select(RestaurantTable)
            .where(RestaurantTable.restaurant_id == restaurant_id)
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

    async def create_table(self, table: RestaurantTable) -> RestaurantTable:
        self.db.add(table)
        await self.db.flush()
        await self.db.refresh(table)
        return table

    async def delete_table(self, table: RestaurantTable) -> None:
        await self.db.delete(table)
        await self.db.flush()

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

    async def has_active_reservations_for_table(self, table_id: int) -> bool:
        result = await self.db.execute(
            select(TableReservation.id).where(
                TableReservation.table_id == table_id,
                TableReservation.status.in_(
                    [ReservationStatus.pending, ReservationStatus.confirmed, ReservationStatus.seated]
                ),
            )
        )
        return result.first() is not None

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

    async def list_restaurant_reservations(
        self,
        *,
        restaurant_id: int,
        reservation_date: date | None = None,
        status: ReservationStatus | None = None,
    ) -> list[TableReservation]:
        conditions = [TableReservation.restaurant_id == restaurant_id]
        if reservation_date is not None:
            conditions.append(TableReservation.reservation_date == reservation_date)
        if status is not None:
            conditions.append(TableReservation.status == status)

        result = await self.db.execute(
            select(TableReservation)
            .where(and_(*conditions))
            .options(
                selectinload(TableReservation.table),
                selectinload(TableReservation.status_events),
                selectinload(TableReservation.restaurant),
                selectinload(TableReservation.customer),
            )
            .order_by(
                TableReservation.reservation_date.desc(),
                TableReservation.reservation_time.desc(),
                TableReservation.id.desc(),
            )
        )
        return list(result.scalars().all())

    async def get_restaurant_reservation(
        self,
        *,
        restaurant_id: int,
        reservation_id: int,
    ) -> TableReservation | None:
        result = await self.db.execute(
            select(TableReservation)
            .where(
                TableReservation.restaurant_id == restaurant_id,
                TableReservation.id == reservation_id,
            )
            .options(
                selectinload(TableReservation.table),
                selectinload(TableReservation.status_events),
                selectinload(TableReservation.restaurant),
                selectinload(TableReservation.customer),
            )
        )
        return result.scalar_one_or_none()

    async def save(self) -> None:
        await self.db.commit()

    async def refresh(self, instance) -> None:
        await self.db.refresh(instance)
