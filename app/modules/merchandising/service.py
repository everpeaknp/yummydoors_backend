from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.merchandising.models import PromoPlacement
from app.modules.merchandising.repository import MerchandisingRepository
from app.modules.merchandising.schemas import FeaturedVideoResponse, PromoBannerResponse


class MerchandisingService:
    def __init__(self, session: AsyncSession):
        self.repository = MerchandisingRepository(session)

    async def list_active_promos(
        self,
        placement: PromoPlacement | None = None,
        global_only: bool = False,
    ) -> list[PromoBannerResponse]:
        promos = await self.repository.list_active_promos(placement, global_only=global_only)
        return [PromoBannerResponse.model_validate(p) for p in promos]

    async def list_active_featured_videos(self, limit: int = 8) -> list[FeaturedVideoResponse]:
        videos = await self.repository.list_active_featured_videos(limit)
        return [FeaturedVideoResponse.model_validate(v) for v in videos]

    async def list_all_featured_videos(self) -> list[FeaturedVideoResponse]:
        videos = await self.repository.list_all_featured_videos()
        return [FeaturedVideoResponse.model_validate(v) for v in videos]

    async def create_featured_video(self, data: dict) -> FeaturedVideoResponse:
        video = await self.repository.create_featured_video(data)
        await self.repository.save()
        await self.repository.refresh(video)
        return FeaturedVideoResponse.model_validate(video)

    async def get_featured_video(self, video_id: int) -> FeaturedVideoResponse | None:
        video = await self.repository.get_featured_video(video_id)
        if video is None:
            return None
        return FeaturedVideoResponse.model_validate(video)

    async def update_featured_video(
        self, video_id: int, data: dict
    ) -> FeaturedVideoResponse | None:
        video = await self.repository.get_featured_video(video_id)
        if video is None:
            return None
        updated = await self.repository.update_featured_video(video, data)
        await self.repository.save()
        await self.repository.refresh(updated)
        return FeaturedVideoResponse.model_validate(updated)

    async def delete_featured_video(self, video_id: int) -> bool:
        video = await self.repository.get_featured_video(video_id)
        if video is None:
            return False
        await self.repository.delete_featured_video(video)
        await self.repository.save()
        return True
