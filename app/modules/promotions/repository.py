from __future__ import annotations

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.promotions.models import Promotion, PromotionRedemption


class PromotionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, code: str) -> Promotion | None:
        result = await self.session.execute(select(Promotion).where(Promotion.code == code))
        return result.scalar_one_or_none()

    async def count_redemptions_for_user(self, *, promotion_id: int, customer_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(PromotionRedemption)
            .where(
                PromotionRedemption.promotion_id == promotion_id,
                PromotionRedemption.customer_id == customer_id,
            )
        )
        return int(result.scalar_one() or 0)

    async def try_claim_usage_slot(self, promotion_id: int) -> bool:
        """Atomically increments `times_used` iff the usage limit (if any)
        isn't already exhausted. Conditional UPDATE + rowcount check avoids
        the same double-spend race that `rider_claim_order` had before it was
        fixed — two concurrent checkouts redeeming the last remaining use of
        a limited-quantity coupon must not both succeed."""
        stmt = (
            update(Promotion)
            .where(
                Promotion.id == promotion_id,
                or_(Promotion.usage_limit.is_(None), Promotion.times_used < Promotion.usage_limit),
            )
            .values(times_used=Promotion.times_used + 1)
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def record_redemption(
        self, *, promotion_id: int, customer_id: int, order_id: int | None, discount_amount: float
    ) -> PromotionRedemption:
        record = PromotionRedemption(
            promotion_id=promotion_id,
            customer_id=customer_id,
            order_id=order_id,
            discount_amount=discount_amount,
        )
        self.session.add(record)
        await self.session.flush()
        return record
