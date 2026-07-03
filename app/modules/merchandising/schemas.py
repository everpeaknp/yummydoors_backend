from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.modules.merchandising.models import PromoPlacement, PromoTargetType

class PromoBannerBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    image_url: str
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
