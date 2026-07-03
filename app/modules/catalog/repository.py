from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.models import MenuItem, MenuModifierGroup


class CatalogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_featured_items(self, limit: int = 10) -> Sequence[MenuItem]:
        stmt = (
            select(MenuItem)
            .where(MenuItem.is_available == True, MenuItem.is_featured == True)
            .order_by(MenuItem.popularity_score.desc(), MenuItem.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_popular_items(self, limit: int = 10) -> Sequence[MenuItem]:
        stmt = (
            select(MenuItem)
            .where(MenuItem.is_available == True, MenuItem.is_popular == True)
            .order_by(MenuItem.popularity_score.desc(), MenuItem.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_menu_by_restaurant(self, restaurant_id: int) -> Sequence[MenuItem]:
        stmt = (
            select(MenuItem)
            .options(selectinload(MenuItem.modifier_groups).selectinload(MenuModifierGroup.items))
            .where(MenuItem.restaurant_id == restaurant_id)
            .order_by(MenuItem.category_id, MenuItem.popularity_score.desc(), MenuItem.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_menu_item_by_slug(self, slug: str) -> MenuItem | None:
        stmt = (
            select(MenuItem)
            .options(selectinload(MenuItem.modifier_groups).selectinload(MenuModifierGroup.items))
            .where(MenuItem.slug == slug)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
