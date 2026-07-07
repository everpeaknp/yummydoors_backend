from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, get_current_user_optional
from app.modules.auth.models import User
from app.modules.catalog.schemas import (
    MerchantMenuItemCreate,
    MerchantMenuItemUpdate,
    MenuItemCreate,
    MenuItemResponse,
    MenuItemSummary,
    MenuItemUpdate,
)
from app.modules.catalog.service import CatalogService
from app.modules.favorites.repository import FavoritesRepository
from app.modules.merchandising.schemas import MerchantPromoCreate, MerchantPromoUpdate, PromoBannerResponse
from app.modules.restaurants.schemas import (
    CategoryCreate,
    MerchantCategoryCreate,
    MerchantCategoryUpdate,
    CategorySummary,
    CategoryUpdate,
    MerchantRestaurantProfileResponse,
    MerchantRestaurantProfileUpdate,
)
from app.schemas.common import ApiResponse

router = APIRouter(tags=["Catalog"])


@router.get("/restaurants/{restaurant_id}/menu", response_model=ApiResponse[List[MenuItemResponse]])
async def get_restaurant_menu(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    service = CatalogService(db)
    items = await service.get_restaurant_menu(restaurant_id)
    favorite_menu_item_ids: set[int] = set()
    if current_user is not None:
        favorite_menu_item_ids = await FavoritesRepository(db).list_favorite_menu_item_ids(current_user.id)
    items = [
        item.model_copy(update={"is_favorited": item.id in favorite_menu_item_ids})
        for item in items
    ]
    return ApiResponse(message="Menu fetched successfully.", data=items)


@router.get("/menu-items/{slug}", response_model=ApiResponse[MenuItemResponse])
async def get_menu_item(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    service = CatalogService(db)
    item = await service.get_menu_item_by_slug(slug)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    if current_user is not None:
        favorite_menu_item_ids = await FavoritesRepository(db).list_favorite_menu_item_ids(current_user.id)
        item = item.model_copy(update={"is_favorited": item.id in favorite_menu_item_ids})
    return ApiResponse(message="Menu item fetched successfully.", data=item)

@router.get(
    "/merchant/restaurants/{restaurant_id}/profile",
    response_model=ApiResponse[MerchantRestaurantProfileResponse],
)
async def get_merchant_restaurant_profile_api(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CatalogService(db)
    profile = await service.get_merchant_restaurant_profile(current_user, restaurant_id)
    return ApiResponse(message="Merchant restaurant profile fetched successfully.", data=profile)


@router.put(
    "/merchant/restaurants/{restaurant_id}/profile",
    response_model=ApiResponse[MerchantRestaurantProfileResponse],
)
async def update_merchant_restaurant_profile_api(
    restaurant_id: int,
    payload: MerchantRestaurantProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CatalogService(db)
    profile = await service.update_merchant_restaurant_profile(current_user, restaurant_id, payload)
    return ApiResponse(message="Merchant restaurant profile updated successfully.", data=profile)

@router.post("/merchant/restaurants/{restaurant_id}/categories", response_model=ApiResponse[CategorySummary])
async def create_category_api(
    restaurant_id: int,
    data: MerchantCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CatalogService(db)
    category = await service.create_category(current_user, restaurant_id, data.model_dump())
    return ApiResponse(message="Category created successfully.", data=CategorySummary.model_validate(category))


@router.put("/merchant/restaurants/{restaurant_id}/categories/{category_id}", response_model=ApiResponse[CategorySummary])
async def update_category_api(
    restaurant_id: int,
    category_id: int,
    data: MerchantCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CatalogService(db)
    category = await service.update_category(
        current_user,
        restaurant_id,
        category_id,
        data.model_dump(exclude_unset=True),
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return ApiResponse(message="Category updated successfully.", data=CategorySummary.model_validate(category))


@router.delete("/merchant/restaurants/{restaurant_id}/categories/{category_id}", response_model=ApiResponse)
async def delete_category_api(
    restaurant_id: int,
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CatalogService(db)
    success = await service.delete_category(current_user, restaurant_id, category_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return ApiResponse(message="Category deleted successfully.", data=None)


@router.get("/merchant/restaurants/{restaurant_id}/categories", response_model=ApiResponse[List[CategorySummary]])
async def list_restaurant_categories_api(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CatalogService(db)
    categories = await service.list_categories(current_user, restaurant_id)
    data = [CategorySummary.model_validate(c) for c in categories]
    return ApiResponse(message="Categories fetched successfully.", data=data)


@router.get("/merchant/restaurants/{restaurant_id}/menu-items", response_model=ApiResponse[List[MenuItemResponse]])
async def list_restaurant_menu_items_api(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CatalogService(db)
    items = await service.list_merchant_menu_items(current_user, restaurant_id)
    return ApiResponse(message="Menu items fetched successfully.", data=items)


@router.post("/merchant/restaurants/{restaurant_id}/menu-items", response_model=ApiResponse[MenuItemSummary])
async def create_menu_item_api(
    restaurant_id: int,
    data: MerchantMenuItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CatalogService(db)
    item = await service.create_menu_item(current_user, restaurant_id, data.model_dump())
    return ApiResponse(message="Menu item created successfully.", data=item)


@router.put("/merchant/restaurants/{restaurant_id}/menu-items/{item_id}", response_model=ApiResponse[MenuItemSummary])
async def update_menu_item_api(
    restaurant_id: int,
    item_id: int,
    data: MerchantMenuItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CatalogService(db)
    item = await service.update_menu_item(
        current_user,
        restaurant_id,
        item_id,
        data.model_dump(exclude_unset=True),
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return ApiResponse(message="Menu item updated successfully.", data=item)


@router.delete("/merchant/restaurants/{restaurant_id}/menu-items/{item_id}", response_model=ApiResponse)
async def delete_menu_item_api(
    restaurant_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = CatalogService(db)
    success = await service.delete_menu_item(current_user, restaurant_id, item_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return ApiResponse(message="Menu item deleted successfully.", data=None)


@router.get(
    "/merchant/restaurants/{restaurant_id}/promos",
    response_model=ApiResponse[List[PromoBannerResponse]],
)
async def list_restaurant_promos_api(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CatalogService(db)
    promos = await service.list_restaurant_promos(current_user, restaurant_id)
    return ApiResponse(message="Merchant promos fetched successfully.", data=promos)


@router.post(
    "/merchant/restaurants/{restaurant_id}/promos",
    response_model=ApiResponse[PromoBannerResponse],
)
async def create_restaurant_promo_api(
    restaurant_id: int,
    payload: MerchantPromoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CatalogService(db)
    promo = await service.create_restaurant_promo(current_user, restaurant_id, payload)
    return ApiResponse(message="Merchant promo created successfully.", data=promo)


@router.put(
    "/merchant/restaurants/{restaurant_id}/promos/{promo_id}",
    response_model=ApiResponse[PromoBannerResponse],
)
async def update_restaurant_promo_api(
    restaurant_id: int,
    promo_id: int,
    payload: MerchantPromoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CatalogService(db)
    promo = await service.update_restaurant_promo(current_user, restaurant_id, promo_id, payload)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo not found")
    return ApiResponse(message="Merchant promo updated successfully.", data=promo)


@router.delete(
    "/merchant/restaurants/{restaurant_id}/promos/{promo_id}",
    response_model=ApiResponse,
)
async def delete_restaurant_promo_api(
    restaurant_id: int,
    promo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CatalogService(db)
    success = await service.delete_restaurant_promo(current_user, restaurant_id, promo_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo not found")
    return ApiResponse(message="Merchant promo deleted successfully.", data=None)
