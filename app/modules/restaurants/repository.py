from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.restaurants.models import Category, Restaurant, RestaurantCategory


class RestaurantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _restaurant_query(self) -> Select[tuple[Restaurant]]:
        return (
            select(Restaurant)
            .options(
                selectinload(Restaurant.category_links).selectinload(RestaurantCategory.category)
            )
            .where(Restaurant.status == "active")
            .order_by(Restaurant.sort_rank.desc(), Restaurant.rating_average.desc(), Restaurant.id.asc())
        )

    async def list_restaurants(self) -> list[Restaurant]:
        result = await self.db.execute(self._restaurant_query())
        return list(result.scalars().unique().all())

    async def count_restaurants(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Restaurant).where(Restaurant.status == "active")
        )
        return int(result.scalar_one() or 0)

    async def list_featured_categories(self) -> list[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.is_active.is_(True), Category.is_featured.is_(True))
            .order_by(Category.sort_order.asc(), Category.id.asc())
        )
        return list(result.scalars().all())
