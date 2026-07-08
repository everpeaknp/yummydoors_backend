from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.merchandising.models import (
    FeaturedVideo,
    PromoBanner,
    PromoPlacement,
    PromoTargetType,
)


class MerchandisingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active_promos(
        self,
        placement: PromoPlacement | None = None,
        global_only: bool = False,
    ) -> Sequence[PromoBanner]:
        now = datetime.now(timezone.utc)

        conditions = [
            PromoBanner.is_active == True,
            or_(PromoBanner.start_at == None, PromoBanner.start_at <= now),
            or_(PromoBanner.end_at == None, PromoBanner.end_at >= now),
        ]

        if placement:
            conditions.append(PromoBanner.placement == placement)

        if global_only:
            conditions.append(PromoBanner.target_type == PromoTargetType.none)

        stmt = (
            select(PromoBanner)
            .where(and_(*conditions))
            .order_by(PromoBanner.sort_order.asc(), PromoBanner.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_active_featured_videos(self, limit: int = 8) -> Sequence[FeaturedVideo]:
        stmt = (
            select(FeaturedVideo)
            .where(FeaturedVideo.is_active == True)
            .order_by(FeaturedVideo.sort_order.asc(), FeaturedVideo.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_all_featured_videos(self) -> Sequence[FeaturedVideo]:
        stmt = select(FeaturedVideo).order_by(
            FeaturedVideo.sort_order.asc(), FeaturedVideo.id.desc()
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_featured_video(self, video_id: int) -> FeaturedVideo | None:
        return await self.session.get(FeaturedVideo, video_id)

    async def create_featured_video(self, data: dict) -> FeaturedVideo:
        video = FeaturedVideo(**data)
        self.session.add(video)
        await self.session.flush()
        return video

    async def update_featured_video(self, video: FeaturedVideo, data: dict) -> FeaturedVideo:
        for key, value in data.items():
            setattr(video, key, value)
        await self.session.flush()
        return video

    async def delete_featured_video(self, video: FeaturedVideo) -> None:
        await self.session.delete(video)
        await self.session.flush()

    async def save(self) -> None:
        await self.session.commit()

    async def refresh(self, instance) -> None:
        await self.session.refresh(instance)
