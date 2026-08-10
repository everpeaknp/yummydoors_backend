from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.orders.models import Order
from app.modules.rider_payouts.review_models import RiderReview
from app.modules.rider_payouts.review_schemas import (
    RiderRatingSummaryResponse,
    RiderReviewEligibilityResponse,
    RiderReviewResponse,
)


class RiderReviewService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_order(self, order_id: int) -> Order | None:
        stmt = select(Order).where(Order.id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_review_for_order(self, order_id: int) -> RiderReview | None:
        stmt = select(RiderReview).where(RiderReview.order_id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_eligibility(self, order_id: int, customer_user_id: int) -> RiderReviewEligibilityResponse:
        order = await self._get_order(order_id)
        if order is None or order.customer_id != customer_user_id:
            return RiderReviewEligibilityResponse(canReview=False, alreadyReviewed=False, reason="Order not found.")
        if order.rider_user_id is None:
            return RiderReviewEligibilityResponse(
                canReview=False, alreadyReviewed=False, reason="This order had no rider assigned."
            )
        if order.delivered_at is None:
            return RiderReviewEligibilityResponse(
                canReview=False, alreadyReviewed=False, reason="This order hasn't been delivered yet."
            )
        existing = await self._get_review_for_order(order_id)
        if existing is not None:
            return RiderReviewEligibilityResponse(canReview=False, alreadyReviewed=True)
        return RiderReviewEligibilityResponse(canReview=True, alreadyReviewed=False)

    async def create_review(
        self, *, order_id: int, customer_user_id: int, rating: float, comment: str | None
    ) -> RiderReviewResponse:
        order = await self._get_order(order_id)
        if order is None or order.customer_id != customer_user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if order.rider_user_id is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This order had no rider assigned.")
        if order.delivered_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="You can only review a rider after delivery."
            )
        existing = await self._get_review_for_order(order_id)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You've already reviewed this delivery.")

        review = RiderReview(
            order_id=order_id,
            rider_user_id=order.rider_user_id,
            customer_user_id=customer_user_id,
            rating=rating,
            comment=comment,
        )
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        return await self._format(review)

    async def _format(self, review: RiderReview) -> RiderReviewResponse:
        stmt = (
            select(RiderReview)
            .options(selectinload(RiderReview.customer), selectinload(RiderReview.order))
            .where(RiderReview.id == review.id)
        )
        result = await self.session.execute(stmt)
        loaded = result.scalar_one()
        return RiderReviewResponse(
            id=loaded.id,
            orderId=loaded.order_id,
            orderNumber=loaded.order.order_number if loaded.order else None,
            riderUserId=loaded.rider_user_id,
            customerName=loaded.customer.full_name if loaded.customer else "Customer",
            rating=loaded.rating,
            comment=loaded.comment,
            isPublished=loaded.is_published,
            createdAt=loaded.created_at,
        )

    async def list_for_rider(
        self, rider_user_id: int, *, published_only: bool = True, limit: int = 50, offset: int = 0
    ) -> list[RiderReviewResponse]:
        stmt = (
            select(RiderReview)
            .options(selectinload(RiderReview.customer), selectinload(RiderReview.order))
            .where(RiderReview.rider_user_id == rider_user_id)
            .order_by(RiderReview.created_at.desc())
        )
        if published_only:
            stmt = stmt.where(RiderReview.is_published.is_(True))
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        reviews = list(result.scalars().all())
        return [
            RiderReviewResponse(
                id=r.id,
                orderId=r.order_id,
                orderNumber=r.order.order_number if r.order else None,
                riderUserId=r.rider_user_id,
                customerName=r.customer.full_name if r.customer else "Customer",
                rating=r.rating,
                comment=r.comment,
                isPublished=r.is_published,
                createdAt=r.created_at,
            )
            for r in reviews
        ]

    async def get_rating_summary(self, rider_user_id: int) -> RiderRatingSummaryResponse:
        stmt = select(func.avg(RiderReview.rating), func.count(RiderReview.id)).where(
            RiderReview.rider_user_id == rider_user_id, RiderReview.is_published.is_(True)
        )
        result = await self.session.execute(stmt)
        avg_rating, total = result.one()
        return RiderRatingSummaryResponse(
            riderUserId=rider_user_id,
            averageRating=round(avg_rating, 2) if avg_rating is not None else None,
            totalReviews=total or 0,
        )

    async def get_rating_summaries(self, rider_user_ids: list[int]) -> dict[int, RiderRatingSummaryResponse]:
        """Batched lookup for surfaces (e.g. dispatch candidate lists) that need
        many riders' ratings at once instead of one query per rider."""
        if not rider_user_ids:
            return {}
        stmt = (
            select(RiderReview.rider_user_id, func.avg(RiderReview.rating), func.count(RiderReview.id))
            .where(RiderReview.rider_user_id.in_(rider_user_ids), RiderReview.is_published.is_(True))
            .group_by(RiderReview.rider_user_id)
        )
        result = await self.session.execute(stmt)
        summaries: dict[int, RiderRatingSummaryResponse] = {}
        for rider_user_id, avg_rating, total in result.all():
            summaries[rider_user_id] = RiderRatingSummaryResponse(
                riderUserId=rider_user_id,
                averageRating=round(avg_rating, 2) if avg_rating is not None else None,
                totalReviews=total or 0,
            )
        return summaries

    # -- Admin moderation --------------------------------------------------

    async def list_all(
        self,
        *,
        rider_user_id: int | None = None,
        published_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RiderReview]:
        stmt = (
            select(RiderReview)
            .options(selectinload(RiderReview.customer), selectinload(RiderReview.order), selectinload(RiderReview.rider))
            .order_by(RiderReview.created_at.desc())
        )
        if rider_user_id is not None:
            stmt = stmt.where(RiderReview.rider_user_id == rider_user_id)
        if published_only:
            stmt = stmt.where(RiderReview.is_published.is_(True))
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, review_id: int) -> RiderReview | None:
        stmt = (
            select(RiderReview)
            .options(selectinload(RiderReview.customer), selectinload(RiderReview.order), selectinload(RiderReview.rider))
            .where(RiderReview.id == review_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_published(self, review: RiderReview, *, is_published: bool) -> RiderReview:
        review.is_published = is_published
        await self.session.commit()
        await self.session.refresh(review)
        return review

    async def delete_review(self, review: RiderReview) -> None:
        await self.session.delete(review)
        await self.session.commit()
