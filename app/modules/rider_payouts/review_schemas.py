from datetime import datetime

from pydantic import BaseModel, Field


class RiderReviewCreate(BaseModel):
    rating: float = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class RiderReviewResponse(BaseModel):
    id: int
    orderId: int
    orderNumber: str | None = None
    riderUserId: int
    customerName: str
    rating: float
    comment: str | None = None
    isPublished: bool = True
    createdAt: datetime


class RiderRatingSummaryResponse(BaseModel):
    riderUserId: int
    averageRating: float | None = None
    totalReviews: int = 0


class RiderReviewEligibilityResponse(BaseModel):
    canReview: bool
    alreadyReviewed: bool
    reason: str | None = None


class AdminRiderReviewResponse(BaseModel):
    id: int
    orderId: int
    orderNumber: str | None = None
    riderUserId: int
    riderName: str
    customerUserId: int
    customerName: str
    rating: float
    comment: str | None = None
    isPublished: bool
    createdAt: datetime


class AdminRiderReviewModerationUpdate(BaseModel):
    isPublished: bool
