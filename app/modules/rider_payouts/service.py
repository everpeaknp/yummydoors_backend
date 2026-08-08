from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.geo import haversine_km
from app.modules.orders.models import Order
from app.modules.rider_payouts.models import RiderPayout
from app.modules.rider_payouts.schemas import RiderPayoutResponse


class RiderPayoutService:
    # Foodmandu's own published in-market formula (Rs. 20 flat for the
    # first 1km, +Rs. 20/km beyond) — the most directly comparable
    # benchmark available since it's the same cities/customers this
    # platform operates in, rather than an invented number.
    BASE_FARE = 20.0
    BASE_FARE_COVERS_KM = 1.0
    PER_KM_RATE = 20.0
    # Matches Pathao's published rider-commission split (rider keeps ~80%).
    RIDER_COMMISSION_RATE_PERCENT = 20.0

    def __init__(self, session: AsyncSession):
        self.session = session

    @classmethod
    def calculate_fare(cls, distance_km: float) -> tuple[float, float, float]:
        """Returns (base_fare, distance_fare, gross_fare)."""
        base_fare = cls.BASE_FARE
        extra_km = max(0.0, distance_km - cls.BASE_FARE_COVERS_KM)
        distance_fare = extra_km * cls.PER_KM_RATE
        return base_fare, distance_fare, base_fare + distance_fare

    async def compute_payout_for_order(self, order: Order) -> RiderPayout | None:
        """Creates the payout row for a delivered order's rider, if
        eligible. Idempotent (order_id is unique on this table) — safe to
        call from both the merchant and rider "mark delivered" paths
        without double-charging."""
        if order.rider_user_id is None or order.rider is None:
            return None
        # Private/preferred riders are employed by the restaurant and paid
        # directly by them — the platform has nothing to pay out here.
        # Freelance (open pool) and platform-onboarded riders both do
        # platform-brokered gig work and get paid the same way.
        if order.rider.rider_work_mode not in {"freelance", "platform"}:
            return None

        existing = await self.session.execute(select(RiderPayout).where(RiderPayout.order_id == order.id))
        if existing.scalar_one_or_none() is not None:
            return None

        restaurant = order.restaurant
        if restaurant is None or restaurant.latitude is None or restaurant.longitude is None:
            return None
        if order.delivery_latitude is None or order.delivery_longitude is None:
            return None

        distance_km = haversine_km(
            restaurant.latitude, restaurant.longitude, order.delivery_latitude, order.delivery_longitude
        )
        base_fare, distance_fare, gross_fare = self.calculate_fare(distance_km)
        commission_amount = round(gross_fare * (self.RIDER_COMMISSION_RATE_PERCENT / 100), 2)
        payout_amount = round(gross_fare - commission_amount, 2)

        payout = RiderPayout(
            order_id=order.id,
            rider_user_id=order.rider_user_id,
            restaurant_id=order.restaurant_id,
            distance_km=round(distance_km, 3),
            base_fare=base_fare,
            distance_fare=round(distance_fare, 2),
            gross_fare=round(gross_fare, 2),
            commission_rate_percent=self.RIDER_COMMISSION_RATE_PERCENT,
            commission_amount=commission_amount,
            payout_amount=payout_amount,
            status="pending",
        )
        self.session.add(payout)
        await self.session.commit()
        await self.session.refresh(payout)
        return payout

    async def list_for_rider(self, rider_user_id: int) -> list[RiderPayoutResponse]:
        stmt = (
            select(RiderPayout)
            .options(
                selectinload(RiderPayout.order),
                selectinload(RiderPayout.restaurant),
                selectinload(RiderPayout.rider),
            )
            .where(RiderPayout.rider_user_id == rider_user_id)
            .order_by(RiderPayout.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_response(payout) for payout in result.scalars().all()]

    async def list_all(self, *, status_filter: str | None = None) -> list[RiderPayoutResponse]:
        stmt = (
            select(RiderPayout)
            .options(
                selectinload(RiderPayout.order),
                selectinload(RiderPayout.restaurant),
                selectinload(RiderPayout.rider),
            )
            .order_by(RiderPayout.created_at.desc())
        )
        if status_filter:
            stmt = stmt.where(RiderPayout.status == status_filter)
        result = await self.session.execute(stmt)
        return [self._to_response(payout) for payout in result.scalars().all()]

    async def mark_paid(self, *, payout_id: int, admin_user_id: int) -> RiderPayoutResponse:
        payout = await self.session.get(RiderPayout, payout_id)
        if payout is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found.")
        if payout.status != "paid":
            payout.status = "paid"
            payout.paid_at = datetime.now(UTC)
            payout.paid_by_user_id = admin_user_id
            await self.session.commit()

        refreshed = await self.session.execute(
            select(RiderPayout)
            .options(
                selectinload(RiderPayout.order),
                selectinload(RiderPayout.restaurant),
                selectinload(RiderPayout.rider),
            )
            .where(RiderPayout.id == payout_id)
        )
        return self._to_response(refreshed.scalar_one())

    @staticmethod
    def _to_response(payout: RiderPayout) -> RiderPayoutResponse:
        return RiderPayoutResponse(
            id=payout.id,
            orderId=payout.order_id,
            orderNumber=payout.order.order_number if payout.order else None,
            riderUserId=payout.rider_user_id,
            riderName=payout.rider.full_name if payout.rider else None,
            restaurantId=payout.restaurant_id,
            restaurantName=payout.restaurant.name if payout.restaurant else None,
            distanceKm=payout.distance_km,
            baseFare=payout.base_fare,
            distanceFare=payout.distance_fare,
            grossFare=payout.gross_fare,
            commissionRatePercent=payout.commission_rate_percent,
            commissionAmount=payout.commission_amount,
            payoutAmount=payout.payout_amount,
            status=payout.status,
            paidAt=payout.paid_at,
            createdAt=payout.created_at,
        )
