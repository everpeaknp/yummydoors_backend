from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.merchandising.repository import MerchandisingRepository
from app.modules.merchandising.schemas import PromoBannerResponse
from app.modules.merchandising.models import PromoPlacement

class MerchandisingService:
    def __init__(self, session: AsyncSession):
        self.repository = MerchandisingRepository(session)

    async def list_active_promos(self, placement: PromoPlacement | None = None) -> list[PromoBannerResponse]:
        promos = await self.repository.list_active_promos(placement)
        return [PromoBannerResponse.model_validate(p) for p in promos]
