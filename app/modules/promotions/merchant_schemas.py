from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.promotions.models import PromotionDiscountType


class MerchantPromotionCreateRequest(BaseModel):
    """Same shape as the admin create request, minus restaurantId -- a
    merchant can only ever create a coupon scoped to their own restaurant,
    so it's derived server-side from their active workspace rather than
    accepted as input (prevents a merchant from creating a platform-wide
    code or one scoped to a restaurant they don't own)."""

    code: str = Field(min_length=2, max_length=64)
    discountType: PromotionDiscountType = PromotionDiscountType.fixed
    discountValue: float = Field(ge=0)
    maxDiscountAmount: float | None = Field(default=None, ge=0)
    minOrderAmount: float = Field(default=0, ge=0)
    startsAt: datetime | None = None
    expiresAt: datetime | None = None
    usageLimit: int | None = Field(default=None, ge=1)
    perUserLimit: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class MerchantPromotionUpdateRequest(BaseModel):
    discountType: PromotionDiscountType | None = None
    discountValue: float | None = Field(default=None, ge=0)
    maxDiscountAmount: float | None = Field(default=None, ge=0)
    minOrderAmount: float | None = Field(default=None, ge=0)
    isActive: bool | None = None
    startsAt: datetime | None = None
    expiresAt: datetime | None = None
    usageLimit: int | None = Field(default=None, ge=1)
    perUserLimit: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=255)
