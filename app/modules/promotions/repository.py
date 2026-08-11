from __future__ import annotations

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.promotions.models import Promotion, PromotionRedemption


class PromotionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, code: str) -> Promotion | None:
        result = await self.session.execute(select(Promotion).where(Promotion.code == code))
        return result.scalar_one_or_none()

    async def get_by_id(self, promotion_id: int) -> Promotion | None:
        stmt = (
            select(Promotion)
            .options(selectinload(Promotion.restaurant))
            .where(Promotion.id == promotion_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code_with_restaurant(self, code: str) -> Promotion | None:
        stmt = (
            select(Promotion)
            .options(selectinload(Promotion.restaurant))
            .where(Promotion.code == code)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, restaurant_id: int | None = None, active_only: bool = False) -> list[Promotion]:
        stmt = select(Promotion).options(selectinload(Promotion.restaurant)).order_by(Promotion.created_at.desc())
        if restaurant_id is not None:
            stmt = stmt.where(Promotion.restaurant_id == restaurant_id)
        if active_only:
            stmt = stmt.where(Promotion.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        code: str,
        discount_type,
        discount_value: float,
        max_discount_amount: float | None,
        min_order_amount: float,
        restaurant_id: int | None,
        starts_at,
        expires_at,
        usage_limit: int | None,
        per_user_limit: int | None,
        description: str | None,
    ) -> Promotion:
        promotion = Promotion(
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            max_discount_amount=max_discount_amount,
            min_order_amount=min_order_amount,
            restaurant_id=restaurant_id,
            starts_at=starts_at,
            expires_at=expires_at,
            usage_limit=usage_limit,
            per_user_limit=per_user_limit,
            description=description,
        )
        self.session.add(promotion)
        await self.session.commit()
        await self.session.refresh(promotion)
        return await self.get_by_id(promotion.id)  # type: ignore[return-value]

    async def update(self, promotion: Promotion, fields: dict) -> Promotion:
        """`fields` should already be pre-filtered to only the keys the
        caller explicitly provided (e.g. via Pydantic's exclude_unset) so an
        omitted field is left untouched but an explicit null still clears a
        nullable column like max_discount_amount."""
        for key, value in fields.items():
            setattr(promotion, key, value)
        await self.session.commit()
        await self.session.refresh(promotion)
        return await self.get_by_id(promotion.id)  # type: ignore[return-value]

    async def delete(self, promotion: Promotion) -> None:
        await self.session.delete(promotion)
        await self.session.commit()

    async def count_redemptions(self, promotion_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(PromotionRedemption).where(PromotionRedemption.promotion_id == promotion_id)
        )
        return int(result.scalar_one() or 0)

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
