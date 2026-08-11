from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from app.modules.promotions.models import PromotionDiscountType

if TYPE_CHECKING:
    from app.modules.promotions.models import Promotion


class PromotionResponse(BaseModel):
    id: int
    code: str
    discountType: PromotionDiscountType
    discountValue: float
    maxDiscountAmount: float | None = None
    minOrderAmount: float
    restaurantId: int | None = None
    restaurantName: str | None = None
    isActive: bool
    startsAt: datetime | None = None
    expiresAt: datetime | None = None
    usageLimit: int | None = None
    perUserLimit: int | None = None
    timesUsed: int
    description: str | None = None
    createdAt: datetime


class PromotionCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    discountType: PromotionDiscountType = PromotionDiscountType.fixed
    discountValue: float = Field(ge=0)
    maxDiscountAmount: float | None = Field(default=None, ge=0)
    minOrderAmount: float = Field(default=0, ge=0)
    restaurantId: int | None = None
    startsAt: datetime | None = None
    expiresAt: datetime | None = None
    usageLimit: int | None = Field(default=None, ge=1)
    perUserLimit: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class PromotionUpdateRequest(BaseModel):
    discountType: PromotionDiscountType | None = None
    discountValue: float | None = Field(default=None, ge=0)
    maxDiscountAmount: float | None = Field(default=None, ge=0)
    minOrderAmount: float | None = Field(default=None, ge=0)
    restaurantId: int | None = None
    isActive: bool | None = None
    startsAt: datetime | None = None
    expiresAt: datetime | None = None
    usageLimit: int | None = Field(default=None, ge=1)
    perUserLimit: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=255)


def format_promotion_response(promotion: "Promotion") -> PromotionResponse:
    return PromotionResponse(
        id=promotion.id,
        code=promotion.code,
        discountType=promotion.discount_type,
        discountValue=promotion.discount_value,
        maxDiscountAmount=promotion.max_discount_amount,
        minOrderAmount=promotion.min_order_amount,
        restaurantId=promotion.restaurant_id,
        restaurantName=promotion.restaurant.name if promotion.restaurant else None,
        isActive=promotion.is_active,
        startsAt=promotion.starts_at,
        expiresAt=promotion.expires_at,
        usageLimit=promotion.usage_limit,
        perUserLimit=promotion.per_user_limit,
        timesUsed=promotion.times_used,
        description=promotion.description,
        createdAt=promotion.created_at,
    )
