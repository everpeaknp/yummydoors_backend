from typing import Sequence
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.merchandising.models import PromoBanner, PromoPlacement

class MerchandisingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active_promos(self, placement: PromoPlacement | None = None) -> Sequence[PromoBanner]:
        now = datetime.now(timezone.utc)
        
        conditions = [
            PromoBanner.is_active == True,
            or_(PromoBanner.start_at == None, PromoBanner.start_at <= now),
            or_(PromoBanner.end_at == None, PromoBanner.end_at >= now),
        ]
        
        if placement:
            conditions.append(PromoBanner.placement == placement)
            
        stmt = (
            select(PromoBanner)
            .where(and_(*conditions))
            .order_by(PromoBanner.sort_order.asc(), PromoBanner.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
