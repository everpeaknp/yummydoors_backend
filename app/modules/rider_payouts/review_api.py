from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.rider_payouts.review import RiderReviewService
from app.modules.rider_payouts.review_schemas import (
    AdminRiderReviewModerationUpdate,
    AdminRiderReviewResponse,
    RiderRatingSummaryResponse,
    RiderReviewCreate,
    RiderReviewEligibilityResponse,
    RiderReviewResponse,
)

router = APIRouter(tags=["Rider Reviews"])


def _format_admin_review(review) -> AdminRiderReviewResponse:
    return AdminRiderReviewResponse(
        id=review.id,
        orderId=review.order_id,
        orderNumber=review.order.order_number if review.order else None,
        riderUserId=review.rider_user_id,
        riderName=review.rider.full_name if review.rider else "Rider",
        customerUserId=review.customer_user_id,
        customerName=review.customer.full_name if review.customer else "Customer",
        rating=review.rating,
        comment=review.comment,
        isPublished=review.is_published,
        createdAt=review.created_at,
    )


@router.get("/orders/{order_id}/rider-review/eligibility", response_model=RiderReviewEligibilityResponse)
async def check_rider_review_eligibility(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderReviewService(db)
    return await service.check_eligibility(order_id, current_user.id)


@router.post(
    "/orders/{order_id}/rider-review",
    response_model=RiderReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rider_review(
    order_id: int,
    payload: RiderReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderReviewService(db)
    return await service.create_review(
        order_id=order_id, customer_user_id=current_user.id, rating=payload.rating, comment=payload.comment
    )


@router.get("/riders/{rider_user_id}/reviews", response_model=List[RiderReviewResponse])
async def list_rider_reviews(
    rider_user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = RiderReviewService(db)
    return await service.list_for_rider(rider_user_id)


@router.get("/riders/{rider_user_id}/rating-summary", response_model=RiderRatingSummaryResponse)
async def get_rider_rating_summary(
    rider_user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = RiderReviewService(db)
    return await service.get_rating_summary(rider_user_id)


@router.get(
    "/admin/rider-reviews",
    response_model=List[AdminRiderReviewResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_admin_rider_reviews(
    rider_user_id: int | None = None,
    published_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    service = RiderReviewService(db)
    reviews = await service.list_all(rider_user_id=rider_user_id, published_only=published_only)
    return [_format_admin_review(r) for r in reviews]


@router.patch(
    "/admin/rider-reviews/{review_id}/moderation",
    response_model=AdminRiderReviewResponse,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def moderate_admin_rider_review(
    review_id: int,
    payload: AdminRiderReviewModerationUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = RiderReviewService(db)
    review = await service.get_by_id(review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    updated = await service.set_published(review, is_published=payload.isPublished)
    return _format_admin_review(updated)


@router.delete(
    "/admin/rider-reviews/{review_id}",
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def delete_admin_rider_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = RiderReviewService(db)
    review = await service.get_by_id(review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    await service.delete_review(review)
    return {"message": "Review deleted."}
