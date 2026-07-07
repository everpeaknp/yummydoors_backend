from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.models import MenuItem
from app.modules.favorites.models import UserFavoriteMenuItem, UserFavoriteRestaurant
from app.modules.restaurants.models import Restaurant, RestaurantCategory


class FavoritesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_restaurant_favorites(self, user_id: int) -> list[UserFavoriteRestaurant]:
        stmt = (
            select(UserFavoriteRestaurant)
            .options(
                selectinload(UserFavoriteRestaurant.restaurant)
                .selectinload(Restaurant.category_links)
                .selectinload(RestaurantCategory.category)
            )
            .where(UserFavoriteRestaurant.user_id == user_id)
            .order_by(UserFavoriteRestaurant.created_at.desc(), UserFavoriteRestaurant.id.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_menu_item_favorites(self, user_id: int) -> list[UserFavoriteMenuItem]:
        stmt = (
            select(UserFavoriteMenuItem)
            .options(
                selectinload(UserFavoriteMenuItem.menu_item).selectinload(MenuItem.restaurant),
                selectinload(UserFavoriteMenuItem.menu_item).selectinload(MenuItem.category),
            )
            .where(UserFavoriteMenuItem.user_id == user_id)
            .order_by(UserFavoriteMenuItem.created_at.desc(), UserFavoriteMenuItem.id.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_favorite_restaurant_ids(self, user_id: int) -> set[int]:
        stmt = select(UserFavoriteRestaurant.restaurant_id).where(UserFavoriteRestaurant.user_id == user_id)
        result = await self.db.execute(stmt)
        return {restaurant_id for restaurant_id in result.scalars().all()}

    async def list_favorite_menu_item_ids(self, user_id: int) -> set[int]:
        stmt = select(UserFavoriteMenuItem.menu_item_id).where(UserFavoriteMenuItem.user_id == user_id)
        result = await self.db.execute(stmt)
        return {menu_item_id for menu_item_id in result.scalars().all()}

    async def get_restaurant_favorite(self, user_id: int, restaurant_id: int) -> UserFavoriteRestaurant | None:
        stmt = select(UserFavoriteRestaurant).where(
            and_(
                UserFavoriteRestaurant.user_id == user_id,
                UserFavoriteRestaurant.restaurant_id == restaurant_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_menu_item_favorite(self, user_id: int, menu_item_id: int) -> UserFavoriteMenuItem | None:
        stmt = select(UserFavoriteMenuItem).where(
            and_(
                UserFavoriteMenuItem.user_id == user_id,
                UserFavoriteMenuItem.menu_item_id == menu_item_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_restaurant(self, restaurant_id: int) -> Restaurant | None:
        stmt = (
            select(Restaurant)
            .options(
                selectinload(Restaurant.category_links).selectinload(RestaurantCategory.category)
            )
            .where(Restaurant.id == restaurant_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().unique().first()

    async def get_menu_item(self, menu_item_id: int) -> MenuItem | None:
        stmt = (
            select(MenuItem)
            .options(selectinload(MenuItem.restaurant), selectinload(MenuItem.category))
            .where(MenuItem.id == menu_item_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def add_restaurant_favorite(self, user_id: int, restaurant_id: int) -> UserFavoriteRestaurant:
        favorite = UserFavoriteRestaurant(user_id=user_id, restaurant_id=restaurant_id)
        self.db.add(favorite)
        await self.db.commit()
        await self.db.refresh(favorite)
        return favorite

    async def add_menu_item_favorite(self, user_id: int, menu_item_id: int) -> UserFavoriteMenuItem:
        favorite = UserFavoriteMenuItem(user_id=user_id, menu_item_id=menu_item_id)
        self.db.add(favorite)
        await self.db.commit()
        await self.db.refresh(favorite)
        return favorite

    async def delete_restaurant_favorite(self, favorite: UserFavoriteRestaurant) -> None:
        await self.db.delete(favorite)
        await self.db.commit()

    async def delete_menu_item_favorite(self, favorite: UserFavoriteMenuItem) -> None:
        await self.db.delete(favorite)
        await self.db.commit()
