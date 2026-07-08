from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.models import MenuItem, MenuModifierGroup
from app.modules.merchandising.models import PromoBanner, PromoTargetType
from app.modules.restaurants.models import Category, Restaurant, RestaurantCategory


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
            .where(MenuItem.is_available == True)
            .order_by(
                MenuItem.favorite_count.desc(),
                MenuItem.popularity_score.desc(),
                MenuItem.is_popular.desc(),
                MenuItem.id.desc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_items_by_restaurants(
        self, restaurant_ids: list[int], limit: int = 8
    ) -> Sequence[MenuItem]:
        stmt = (
            select(MenuItem)
            .where(
                MenuItem.restaurant_id.in_(restaurant_ids),
                MenuItem.is_available == True,
            )
            .order_by(
                MenuItem.favorite_count.desc(),
                MenuItem.is_featured.desc(),
                MenuItem.popularity_score.desc(),
                MenuItem.id.desc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_menu_by_restaurant(self, restaurant_id: int) -> Sequence[MenuItem]:
        stmt = (
            select(MenuItem)
            .options(
                selectinload(MenuItem.category),
                selectinload(MenuItem.modifier_groups).selectinload(MenuModifierGroup.items),
            )
            .where(MenuItem.restaurant_id == restaurant_id)
            .order_by(MenuItem.category_id, MenuItem.popularity_score.desc(), MenuItem.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_featured_items_by_restaurant(
        self, restaurant_id: int, limit: int = 8
    ) -> Sequence[MenuItem]:
        stmt = (
            select(MenuItem)
            .where(
                MenuItem.restaurant_id == restaurant_id,
                MenuItem.is_available == True,
                MenuItem.is_featured == True,
            )
            .order_by(MenuItem.popularity_score.desc(), MenuItem.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_popular_items_by_restaurant(
        self, restaurant_id: int, limit: int = 8
    ) -> Sequence[MenuItem]:
        stmt = (
            select(MenuItem)
            .where(
                MenuItem.restaurant_id == restaurant_id,
                MenuItem.is_available == True,
                MenuItem.is_popular == True,
            )
            .order_by(MenuItem.popularity_score.desc(), MenuItem.id.desc())
            .limit(limit)
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

    async def get_restaurant_with_categories(self, restaurant_id: int) -> Restaurant | None:
        stmt = (
            select(Restaurant)
            .options(
                selectinload(Restaurant.category_links).selectinload(RestaurantCategory.category)
            )
            .where(Restaurant.id == restaurant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().first()

    async def list_restaurant_categories(self, restaurant_id: int) -> Sequence[Category]:
        stmt = (
            select(Category)
            .join(RestaurantCategory, RestaurantCategory.category_id == Category.id)
            .where(RestaurantCategory.restaurant_id == restaurant_id)
            .order_by(Category.sort_order.asc(), Category.id.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_category_by_id(self, category_id: int) -> Category | None:
        return await self.session.get(Category, category_id)

    async def get_category_by_slug(self, slug: str) -> Category | None:
        stmt = select(Category).where(Category.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_restaurant_by_slug(self, slug: str) -> Restaurant | None:
        stmt = select(Restaurant).where(Restaurant.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def is_category_linked_to_restaurant(self, restaurant_id: int, category_id: int) -> bool:
        stmt = select(RestaurantCategory).where(
            RestaurantCategory.restaurant_id == restaurant_id,
            RestaurantCategory.category_id == category_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def link_category_to_restaurant(self, restaurant_id: int, category_id: int) -> None:
        if await self.is_category_linked_to_restaurant(restaurant_id, category_id):
            return
        self.session.add(RestaurantCategory(restaurant_id=restaurant_id, category_id=category_id))
        await self.session.flush()

    async def unlink_category_from_restaurant(self, restaurant_id: int, category_id: int) -> None:
        stmt = select(RestaurantCategory).where(
            RestaurantCategory.restaurant_id == restaurant_id,
            RestaurantCategory.category_id == category_id,
        )
        result = await self.session.execute(stmt)
        link = result.scalar_one_or_none()
        if link is not None:
            await self.session.delete(link)
            await self.session.flush()

    async def create_category(self, data: dict):
        category = Category(**data)
        self.session.add(category)
        await self.session.flush()
        return category

    async def save(self) -> None:
        await self.session.commit()

    async def refresh(self, instance) -> None:
        await self.session.refresh(instance)

    async def null_menu_item_category_for_restaurant(
        self, restaurant_id: int, category_id: int
    ) -> None:
        stmt = select(MenuItem).where(
            MenuItem.restaurant_id == restaurant_id,
            MenuItem.category_id == category_id,
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        for item in items:
            item.category_id = None
        await self.session.flush()

    async def category_link_count(self, category_id: int) -> int:
        stmt = select(RestaurantCategory).where(RestaurantCategory.category_id == category_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def update_category(self, category_id: int, data: dict):
        category = await self.session.get(Category, category_id)
        if not category:
            return None
        for k, v in data.items():
            setattr(category, k, v)
        await self.session.flush()
        return category

    async def delete_category(self, category_id: int) -> bool:
        category = await self.session.get(Category, category_id)
        if not category:
            return False
        await self.session.delete(category)
        await self.session.flush()
        return True

    async def list_categories(self) -> Sequence[Category]:
        stmt = select(Category).order_by(Category.sort_order.asc(), Category.id.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_menu_item(self, restaurant_id: int, data: dict) -> MenuItem:
        item = MenuItem(restaurant_id=restaurant_id, **data)
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_menu_item_by_id(self, item_id: int) -> MenuItem | None:
        stmt = (
            select(MenuItem)
            .options(
                selectinload(MenuItem.category),
                selectinload(MenuItem.modifier_groups).selectinload(MenuModifierGroup.items),
            )
            .where(MenuItem.id == item_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_menu_item(self, item_id: int, data: dict) -> MenuItem | None:
        item = await self.session.get(MenuItem, item_id)
        if not item:
            return None
        for k, v in data.items():
            setattr(item, k, v)
        await self.session.flush()
        return item

    async def delete_menu_item(self, item_id: int) -> bool:
        item = await self.session.get(MenuItem, item_id)
        if not item:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def list_restaurant_promos(self, restaurant_id: int) -> Sequence[PromoBanner]:
        stmt = (
            select(PromoBanner)
            .where(
                PromoBanner.target_type == PromoTargetType.restaurant,
                PromoBanner.target_id == restaurant_id,
            )
            .order_by(PromoBanner.sort_order.asc(), PromoBanner.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_restaurant_promo(self, restaurant_id: int, promo_id: int) -> PromoBanner | None:
        stmt = select(PromoBanner).where(
            PromoBanner.id == promo_id,
            PromoBanner.target_type == PromoTargetType.restaurant,
            PromoBanner.target_id == restaurant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_restaurant_promo(self, restaurant_id: int, data: dict) -> PromoBanner:
        promo = PromoBanner(
            **data,
            target_type=PromoTargetType.restaurant,
            target_id=restaurant_id,
        )
        self.session.add(promo)
        await self.session.flush()
        return promo

    async def update_restaurant_promo(self, promo: PromoBanner, data: dict) -> PromoBanner:
        for key, value in data.items():
            setattr(promo, key, value)
        await self.session.flush()
        return promo

    async def delete_restaurant_promo(self, promo: PromoBanner) -> None:
        await self.session.delete(promo)
        await self.session.flush()
