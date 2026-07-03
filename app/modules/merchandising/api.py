from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.modules.merchandising.schemas import PromoBannerResponse
from app.modules.merchandising.service import MerchandisingService
from app.modules.merchandising.models import PromoPlacement

router = APIRouter(tags=["merchandising"])

@router.get("/promos", response_model=ApiResponse[List[PromoBannerResponse]])
async def list_promos(
    placement: PromoPlacement | None = None,
    db: AsyncSession = Depends(get_db)
):
    service = MerchandisingService(db)
    promos = await service.list_active_promos(placement)
    return ApiResponse(message="Promos fetched successfully.", data=promos)
