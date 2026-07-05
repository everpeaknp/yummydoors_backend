from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.modules.merchandising.models import PromoPlacement, PromoTargetType

class PromoBannerBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    image_url: str
    image_url_mobile: Optional[str] = None
    placement: PromoPlacement
    target_type: PromoTargetType
    target_id: Optional[int] = None
    target_url: Optional[str] = None
    cta_text: Optional[str] = None
    sort_order: int = 0

class PromoBannerResponse(PromoBannerBase):
    id: int
    is_active: bool
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MerchantPromoCreate(BaseModel):
    title: str = Field(..., max_length=255)
    subtitle: str | None = Field(default=None, max_length=255)
    image_url: str = Field(..., max_length=500)
    image_url_mobile: str | None = Field(default=None, max_length=500)
    placement: PromoPlacement
    target_url: str | None = Field(default=None, max_length=500)
    cta_text: str | None = Field(default=None, max_length=100)
    sort_order: int = 0
    is_active: bool = True
    start_at: datetime | None = None
    end_at: datetime | None = None


class MerchantPromoUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    subtitle: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=500)
    image_url_mobile: str | None = Field(default=None, max_length=500)
    placement: PromoPlacement | None = None
    target_url: str | None = Field(default=None, max_length=500)
    cta_text: str | None = Field(default=None, max_length=100)
    sort_order: int | None = None
    is_active: bool | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
