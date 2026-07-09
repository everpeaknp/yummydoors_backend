from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.restaurants.models import RestaurantReview

class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_reviews(self, restaurant_id: int) -> list[RestaurantReview]:
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.user))
            .where(RestaurantReview.restaurant_id == restaurant_id)
            .order_by(RestaurantReview.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, review_id: int) -> RestaurantReview | None:
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.user))
            .where(RestaurantReview.id == review_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_review(
        self,
        *,
        user_id: int,
        restaurant_id: int,
        rating: int,
        content: str | None,
    ) -> RestaurantReview:
        review = RestaurantReview(
            user_id=user_id,
            restaurant_id=restaurant_id,
            rating=rating,
            comment=content,
            author_name="Anonymous" # this is a fallback if needed
        )
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.user))
            .where(RestaurantReview.id == review.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def add_reply(self, review: RestaurantReview, reply: str) -> RestaurantReview:
        review.merchant_reply = reply
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def count_new_reviews(self, restaurant_id: int, since_days: int = 7) -> int:
        from datetime import UTC, datetime, timedelta
        from sqlalchemy import func
        cutoff = datetime.now(UTC) - timedelta(days=since_days)
        stmt = select(func.count()).where(
            MerchantReview.restaurant_id == restaurant_id,
            MerchantReview.created_at >= cutoff,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
