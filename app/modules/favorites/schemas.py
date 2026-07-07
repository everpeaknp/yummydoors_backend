from __future__ import annotations

from pydantic import BaseModel

from app.modules.catalog.schemas import MenuItemSummary
from app.modules.restaurants.schemas import RestaurantCardSummary


class FavoriteRestaurantResponse(BaseModel):
    id: int
    created_at: str
    restaurant: RestaurantCardSummary


class FavoriteMenuItemResponse(BaseModel):
    id: int
    created_at: str
    menu_item: MenuItemSummary
    restaurant: RestaurantCardSummary


class FavoritesResponse(BaseModel):
    restaurants: list[FavoriteRestaurantResponse] = []
    menu_items: list[FavoriteMenuItemResponse] = []
    restaurant_ids: list[int] = []
    menu_item_ids: list[int] = []
