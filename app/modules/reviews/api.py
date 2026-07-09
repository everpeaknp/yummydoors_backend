from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.schemas import ReplyRequest, ReviewCreate, ReviewResponse
from app.modules.workspaces.repository import WorkspaceRepository

router = APIRouter(prefix="/reviews", tags=["Reviews"])


async def _get_merchant_restaurant_id(user_id: int, session: AsyncSession) -> int:
    workspace_repo = WorkspaceRepository(session)
    workspace = await workspace_repo.get_active_workspace(user_id)
    if not workspace or workspace.workspace_type != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active workspace is not a merchant workspace.",
        )
    if not workspace.primary_restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active restaurant in this workspace.",
        )
    return workspace.primary_restaurant_id


@router.get("/merchant/me", response_model=list[ReviewResponse])
async def list_merchant_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
    repo = ReviewRepository(db)
    reviews = await repo.list_reviews(restaurant_id)
    return [
        ReviewResponse(
            id=r.id,
            user_id=r.user_id,
            reviewer_name=r.user.full_name if r.user else r.author_name,
            rating=r.rating,
            content=r.comment,
            merchant_reply=r.merchant_reply,
            created_at=r.created_at,
        )
        for r in reviews
    ]


@router.post(
    "/merchant/{review_id}/reply",
    response_model=ReviewResponse,
)
async def reply_to_review(
    review_id: int,
    payload: ReplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
    repo = ReviewRepository(db)
    review = await repo.get_by_id(review_id)
    if review is None or review.restaurant_id != restaurant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    updated = await repo.add_reply(review, payload.reply)
    return ReviewResponse(
        id=updated.id,
        user_id=updated.user_id,
        reviewer_name=updated.user.full_name if updated.user else updated.author_name,
        rating=updated.rating,
        content=updated.comment,
        merchant_reply=updated.merchant_reply,
        created_at=updated.created_at,
    )


@router.post(
    "/customer/{restaurant_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    restaurant_id: int,
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Customer endpoint to submit a review for a restaurant."""
    repo = ReviewRepository(db)
    review = await repo.create_review(
        user_id=current_user.id,
        restaurant_id=restaurant_id,
        rating=payload.rating,
        content=payload.content,
    )
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        reviewer_name=review.user.full_name if review.user else review.author_name,
        rating=review.rating,
        content=review.comment,
        merchant_reply=review.merchant_reply,
        created_at=review.created_at,
    )
