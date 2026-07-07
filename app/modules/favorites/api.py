from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.favorites.repository import FavoritesRepository
from app.modules.favorites.schemas import (
    FavoriteMenuItemResponse,
    FavoriteRestaurantResponse,
    FavoritesResponse,
)
from app.modules.restaurants.api import build_restaurant_summary_with_context
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/favorites", tags=["Favorites"])


def get_favorites_repository(db=Depends(get_db)) -> FavoritesRepository:
    return FavoritesRepository(db)


@router.get(
    "",
    response_model=ApiResponse[FavoritesResponse],
    summary="List my wishlist and favorites",
)
async def list_favorites(
    current_user: User = Depends(get_current_user),
    repo: FavoritesRepository = Depends(get_favorites_repository),
):
    restaurant_favorites = await repo.list_restaurant_favorites(current_user.id)
    menu_item_favorites = await repo.list_menu_item_favorites(current_user.id)

    data = FavoritesResponse(
        restaurants=[
            FavoriteRestaurantResponse(
                id=favorite.id,
                created_at=favorite.created_at.isoformat(),
                restaurant=build_restaurant_summary_with_context(
                    restaurant=favorite.restaurant,
                    latitude=None,
                    longitude=None,
                ),
            )
            for favorite in restaurant_favorites
            if favorite.restaurant is not None
        ],
        menu_items=[
            FavoriteMenuItemResponse(
                id=favorite.id,
                created_at=favorite.created_at.isoformat(),
                menu_item=MenuItemSummary.model_validate(favorite.menu_item),
                restaurant=build_restaurant_summary_with_context(
                    restaurant=favorite.menu_item.restaurant,
                    latitude=None,
                    longitude=None,
                ),
            )
            for favorite in menu_item_favorites
            if favorite.menu_item is not None and favorite.menu_item.restaurant is not None
        ],
        restaurant_ids=sorted({favorite.restaurant_id for favorite in restaurant_favorites}),
        menu_item_ids=sorted({favorite.menu_item_id for favorite in menu_item_favorites}),
    )
    return ApiResponse(message="Favorites fetched successfully.", data=data)


@router.post(
    "/restaurants/{restaurant_id}",
    response_model=ApiResponse[FavoriteRestaurantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add restaurant to wishlist",
)
async def favorite_restaurant(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    repo: FavoritesRepository = Depends(get_favorites_repository),
):
    restaurant = await repo.get_restaurant(restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")

    existing = await repo.get_restaurant_favorite(current_user.id, restaurant_id)
    favorite = existing or await repo.add_restaurant_favorite(current_user.id, restaurant_id)

    data = FavoriteRestaurantResponse(
        id=favorite.id,
        created_at=favorite.created_at.isoformat() if favorite.created_at else "",
        restaurant=build_restaurant_summary_with_context(
            restaurant=restaurant,
            latitude=None,
            longitude=None,
        ),
    )
    return ApiResponse(message="Restaurant saved to favorites.", data=data)


@router.delete(
    "/restaurants/{restaurant_id}",
    response_model=ApiResponse[dict],
    summary="Remove restaurant from wishlist",
)
async def unfavorite_restaurant(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    repo: FavoritesRepository = Depends(get_favorites_repository),
):
    favorite = await repo.get_restaurant_favorite(current_user.id, restaurant_id)
    if favorite is None:
        return ApiResponse(message="Restaurant was already removed from favorites.", data={"restaurant_id": restaurant_id})

    await repo.delete_restaurant_favorite(favorite)
    return ApiResponse(message="Restaurant removed from favorites.", data={"restaurant_id": restaurant_id})


@router.post(
    "/menu-items/{menu_item_id}",
    response_model=ApiResponse[FavoriteMenuItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add menu item to wishlist",
)
async def favorite_menu_item(
    menu_item_id: int,
    current_user: User = Depends(get_current_user),
    repo: FavoritesRepository = Depends(get_favorites_repository),
):
    menu_item = await repo.get_menu_item(menu_item_id)
    if menu_item is None or menu_item.restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")

    existing = await repo.get_menu_item_favorite(current_user.id, menu_item_id)
    favorite = existing or await repo.add_menu_item_favorite(current_user.id, menu_item_id)

    data = FavoriteMenuItemResponse(
        id=favorite.id,
        created_at=favorite.created_at.isoformat() if favorite.created_at else "",
        menu_item=MenuItemSummary.model_validate(menu_item),
        restaurant=build_restaurant_summary_with_context(
            restaurant=menu_item.restaurant,
            latitude=None,
            longitude=None,
        )
    )
    return ApiResponse(message="Menu item saved to favorites.", data=data)


@router.delete(
    "/menu-items/{menu_item_id}",
    response_model=ApiResponse[dict],
    summary="Remove menu item from wishlist",
)
async def unfavorite_menu_item(
    menu_item_id: int,
    current_user: User = Depends(get_current_user),
    repo: FavoritesRepository = Depends(get_favorites_repository),
):
    favorite = await repo.get_menu_item_favorite(current_user.id, menu_item_id)
    if favorite is None:
        return ApiResponse(message="Menu item was already removed from favorites.", data={"menu_item_id": menu_item_id})

    await repo.delete_menu_item_favorite(favorite)
    return ApiResponse(message="Menu item removed from favorites.", data={"menu_item_id": menu_item_id})
