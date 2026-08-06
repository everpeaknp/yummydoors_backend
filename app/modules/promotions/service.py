from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.promotions.models import Promotion, PromotionDiscountType
from app.modules.promotions.repository import PromotionRepository


@dataclass(frozen=True)
class PromotionQuote:
    promotion_id: int
    discount_amount: float
    free_delivery: bool


class PromotionService:
    """Central coupon/promotion engine.

    Replaces the hardcoded WELCOME50/SAVE10/FREEDEL string comparisons that
    used to live independently in CartService and OrderService.get_order_summary
    (the two had already drifted into two separate copies of the same rules).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PromotionRepository(session)

    async def quote_discount(
        self,
        *,
        code: str,
        restaurant_id: int,
        customer_id: int | None,
        items_total: float,
    ) -> PromotionQuote:
        promotion = await self.repo.get_by_code(code.strip().upper())
        if promotion is None or not self._is_eligible(promotion, restaurant_id=restaurant_id, items_total=items_total):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid coupon code.")

        if promotion.usage_limit is not None and promotion.times_used >= promotion.usage_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This coupon has been fully redeemed.")

        if promotion.per_user_limit is not None and customer_id is not None:
            used_by_customer = await self.repo.count_redemptions_for_user(
                promotion_id=promotion.id, customer_id=customer_id
            )
            if used_by_customer >= promotion.per_user_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="You've already used this coupon."
                )

        return self._build_quote(promotion, items_total=items_total)

    async def redeem(
        self,
        *,
        code: str,
        customer_id: int,
        order_id: int,
        discount_amount: float,
    ) -> None:
        """Records a redemption against a just-placed order, atomically
        consuming one usage slot. Called only once checkout actually
        succeeds — never during pricing preview — so previewing a cart never
        burns down a limited-quantity coupon's supply."""
        promotion = await self.repo.get_by_code(code.strip().upper())
        if promotion is None:
            return
        claimed = await self.repo.try_claim_usage_slot(promotion.id)
        if not claimed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This coupon has been fully redeemed.")
        await self.repo.record_redemption(
            promotion_id=promotion.id,
            customer_id=customer_id,
            order_id=order_id,
            discount_amount=discount_amount,
        )

    @staticmethod
    def _is_eligible(promotion: Promotion, *, restaurant_id: int, items_total: float) -> bool:
        if not promotion.is_active:
            return False
        if promotion.restaurant_id is not None and promotion.restaurant_id != restaurant_id:
            return False
        now = datetime.now(UTC)
        if promotion.starts_at is not None and now < promotion.starts_at:
            return False
        if promotion.expires_at is not None and now > promotion.expires_at:
            return False
        if items_total < promotion.min_order_amount:
            return False
        return True

    @staticmethod
    def _build_quote(promotion: Promotion, *, items_total: float) -> PromotionQuote:
        if promotion.discount_type == PromotionDiscountType.free_delivery:
            return PromotionQuote(promotion_id=promotion.id, discount_amount=0.0, free_delivery=True)

        if promotion.discount_type == PromotionDiscountType.percentage:
            discount = items_total * promotion.discount_value / 100
            if promotion.max_discount_amount is not None:
                discount = min(discount, promotion.max_discount_amount)
        else:
            discount = promotion.discount_value

        discount = round(min(max(discount, 0.0), items_total), 2)
        return PromotionQuote(promotion_id=promotion.id, discount_amount=discount, free_delivery=False)
