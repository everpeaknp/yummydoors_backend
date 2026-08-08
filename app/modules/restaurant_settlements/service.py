from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.orders.models import Order
from app.modules.restaurant_settlements.models import RestaurantSettlement
from app.modules.restaurant_settlements.schemas import RestaurantSettlementResponse

# Cash-on-delivery: the merchant already has the customer's cash in hand,
# so the platform's commission is a debt the merchant owes back — everything
# else (esewa, card, etc.) means the platform is already holding the money
# and owes the merchant their share instead.
_COD_PAYMENT_METHODS = {"cash", "cod"}


class RestaurantSettlementService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def compute_settlement_for_order(self, order: Order) -> RestaurantSettlement | None:
        """Creates the settlement row for a delivered order, if eligible.
        Idempotent (order_id is unique on this table) — safe to call from
        both the merchant and rider "mark delivered" paths."""
        if order.restaurant is None:
            return None

        existing = await self.session.execute(
            select(RestaurantSettlement).where(RestaurantSettlement.order_id == order.id)
        )
        if existing.scalar_one_or_none() is not None:
            return None

        payment_method = (order.payment_method or "cash").strip().lower()
        direction = "collect_from_merchant" if payment_method in _COD_PAYMENT_METHODS else "pay_to_merchant"
        rate = order.restaurant.commission_rate_percent
        commission_amount = round(order.subtotal_amount * (rate / 100), 2)

        settlement = RestaurantSettlement(
            order_id=order.id,
            restaurant_id=order.restaurant_id,
            payment_method=payment_method,
            direction=direction,
            subtotal_amount=order.subtotal_amount,
            commission_rate_percent=rate,
            commission_amount=commission_amount,
            status="pending",
        )
        self.session.add(settlement)
        await self.session.commit()
        await self.session.refresh(settlement)
        return settlement

    async def list_for_restaurant(self, restaurant_id: int) -> list[RestaurantSettlementResponse]:
        stmt = (
            select(RestaurantSettlement)
            .options(selectinload(RestaurantSettlement.order), selectinload(RestaurantSettlement.restaurant))
            .where(RestaurantSettlement.restaurant_id == restaurant_id)
            .order_by(RestaurantSettlement.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_response(row) for row in result.scalars().all()]

    async def list_all(self, *, status_filter: str | None = None) -> list[RestaurantSettlementResponse]:
        stmt = (
            select(RestaurantSettlement)
            .options(selectinload(RestaurantSettlement.order), selectinload(RestaurantSettlement.restaurant))
            .order_by(RestaurantSettlement.created_at.desc())
        )
        if status_filter:
            stmt = stmt.where(RestaurantSettlement.status == status_filter)
        result = await self.session.execute(stmt)
        return [self._to_response(row) for row in result.scalars().all()]

    async def mark_settled(self, *, settlement_id: int, admin_user_id: int) -> RestaurantSettlementResponse:
        settlement = await self.session.get(RestaurantSettlement, settlement_id)
        if settlement is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found.")
        if settlement.status != "settled":
            settlement.status = "settled"
            settlement.settled_at = datetime.now(UTC)
            settlement.settled_by_user_id = admin_user_id
            await self.session.commit()

        refreshed = await self.session.execute(
            select(RestaurantSettlement)
            .options(selectinload(RestaurantSettlement.order), selectinload(RestaurantSettlement.restaurant))
            .where(RestaurantSettlement.id == settlement_id)
        )
        return self._to_response(refreshed.scalar_one())

    @staticmethod
    def _to_response(settlement: RestaurantSettlement) -> RestaurantSettlementResponse:
        return RestaurantSettlementResponse(
            id=settlement.id,
            orderId=settlement.order_id,
            orderNumber=settlement.order.order_number if settlement.order else None,
            restaurantId=settlement.restaurant_id,
            restaurantName=settlement.restaurant.name if settlement.restaurant else None,
            paymentMethod=settlement.payment_method,
            direction=settlement.direction,
            subtotalAmount=settlement.subtotal_amount,
            commissionRatePercent=settlement.commission_rate_percent,
            commissionAmount=settlement.commission_amount,
            status=settlement.status,
            settledAt=settlement.settled_at,
            createdAt=settlement.created_at,
        )
