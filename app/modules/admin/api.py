from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.modules.auth.deps import require_role
from app.modules.auth.models import User
from app.services.cloudinary_service import CloudinaryService
from app.modules.catalog.models import MenuItem
from app.modules.merchandising.models import PromoBanner
from app.modules.reservations.models import ReservationStatus
from app.modules.reservations.schemas import (
    ReservationResponse,
    ReservationStatusUpdateRequest,
    RestaurantTableCreateRequest,
    RestaurantTableSummary,
    RestaurantTableUpdateRequest,
)
from app.modules.reservations.service import ReservationService
from app.modules.restaurants.models import Category, Restaurant, RestaurantCategory
from app.modules.admin.schemas import (
    AdminCategoryCreate,
    AdminCategoryResponse,
    AdminCategoryUpdate,
    AdminMenuItemCreate,
    AdminMenuItemResponse,
    AdminMenuItemUpdate,
    AdminPromoCreate,
    AdminPromoResponse,
    AdminPromoUpdate,
    AdminRestaurantCreate,
    AdminRestaurantResponse,
    AdminRestaurantUpdate,
)
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


def _restaurant_query():
    return select(Restaurant).options(
        selectinload(Restaurant.category_links).selectinload(RestaurantCategory.category)
    )


def _build_category_response(category: Category) -> AdminCategoryResponse:
    return AdminCategoryResponse.model_validate(category)


def _build_restaurant_response(restaurant: Restaurant) -> AdminRestaurantResponse:
    categories = [
        AdminCategoryResponse.model_validate(link.category)
        for link in sorted(
            restaurant.category_links,
            key=lambda item: (item.category.sort_order, item.category.id),
        )
        if link.category is not None
    ]
    return AdminRestaurantResponse(
        id=restaurant.id,
        name=restaurant.name,
        slug=restaurant.slug,
        integration_mode=restaurant.integration_mode,
        status=restaurant.status,
        cover_image_url=restaurant.cover_image_url,
        logo_url=restaurant.logo_url,
        short_description=restaurant.short_description,
        primary_cuisine_label=restaurant.primary_cuisine_label,
        city=restaurant.city,
        area=restaurant.area,
        latitude=restaurant.latitude,
        longitude=restaurant.longitude,
        rating_average=restaurant.rating_average,
        review_count=restaurant.review_count,
        supports_delivery=restaurant.supports_delivery,
        has_free_delivery=restaurant.has_free_delivery,
        offer_text=restaurant.offer_text,
        delivery_eta_min_minutes=restaurant.delivery_eta_min_minutes,
        delivery_eta_max_minutes=restaurant.delivery_eta_max_minutes,
        sort_rank=restaurant.sort_rank,
        is_featured=restaurant.is_featured,
        categories=categories,
    )


async def _get_category_or_404(db: AsyncSession, category_id: int) -> Category:
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    return category


async def _get_restaurant_or_404(db: AsyncSession, restaurant_id: int) -> Restaurant:
    restaurant = await db.scalar(_restaurant_query().where(Restaurant.id == restaurant_id))
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
    return restaurant


async def _get_menu_item_or_404(db: AsyncSession, menu_item_id: int) -> MenuItem:
    menu_item = await db.get(MenuItem, menu_item_id)
    if menu_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")
    return menu_item


async def _get_promo_or_404(db: AsyncSession, promo_id: int) -> PromoBanner:
    promo = await db.get(PromoBanner, promo_id)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo not found.")
    return promo


async def _replace_restaurant_categories(
    db: AsyncSession,
    restaurant: Restaurant,
    category_ids: list[int],
) -> None:
    result = await db.execute(select(Category).where(Category.id.in_(category_ids)))
    categories = list(result.scalars().all())
    found_ids = {category.id for category in categories}
    missing_ids = sorted(set(category_ids) - found_ids)
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown category ids: {missing_ids}",
        )

    current_links = {link.category_id: link for link in restaurant.category_links}
    desired_ids = set(category_ids)

    for category_id, link in list(current_links.items()):
        if category_id not in desired_ids:
            await db.delete(link)

    existing_ids = set(current_links)
    for category in categories:
        if category.id not in existing_ids:
            db.add(RestaurantCategory(restaurant_id=restaurant.id, category_id=category.id))


@router.get(
    "/categories",
    response_model=ApiResponse[list[AdminCategoryResponse]],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order.asc(), Category.id.asc()))
    items = [
        _build_category_response(category)
        for category in result.scalars().all()
    ]
    return ApiResponse(message="Admin categories fetched successfully.", data=items)


@router.post(
    "/categories",
    response_model=ApiResponse[AdminCategoryResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def create_category(payload: AdminCategoryCreate, db: AsyncSession = Depends(get_db)):
    category = Category(**payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return ApiResponse(
        message="Admin category created successfully.",
        data=_build_category_response(category),
    )


@router.put(
    "/categories/{category_id}",
    response_model=ApiResponse[AdminCategoryResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def update_category(
    category_id: int,
    payload: AdminCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    category = await _get_category_or_404(db, category_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return ApiResponse(
        message="Admin category updated successfully.",
        data=_build_category_response(category),
    )


@router.delete(
    "/categories/{category_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await _get_category_or_404(db, category_id)
    await db.delete(category)
    await db.commit()
    return ApiResponse(message="Admin category deleted successfully.", data={"success": True})


@router.get(
    "/restaurants",
    response_model=ApiResponse[list[AdminRestaurantResponse]],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def list_admin_restaurants(db: AsyncSession = Depends(get_db)):
    result = await db.execute(_restaurant_query().order_by(Restaurant.id.desc()))
    items = [_build_restaurant_response(restaurant) for restaurant in result.scalars().unique().all()]
    return ApiResponse(message="Admin restaurants fetched successfully.", data=items)


@router.post(
    "/restaurants",
    response_model=ApiResponse[AdminRestaurantResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def create_restaurant(payload: AdminRestaurantCreate, db: AsyncSession = Depends(get_db)):
    restaurant_data = payload.model_dump(exclude={"category_ids"})
    restaurant = Restaurant(**restaurant_data)
    db.add(restaurant)
    await db.flush()
    await _replace_restaurant_categories(db, restaurant, payload.category_ids)
    await db.commit()
    restaurant = await _get_restaurant_or_404(db, restaurant.id)
    return ApiResponse(
        message="Admin restaurant created successfully.",
        data=_build_restaurant_response(restaurant),
    )


@router.get(
    "/restaurants/{restaurant_id}",
    response_model=ApiResponse[AdminRestaurantResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def get_admin_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    restaurant = await _get_restaurant_or_404(db, restaurant_id)
    return ApiResponse(
        message="Admin restaurant fetched successfully.",
        data=_build_restaurant_response(restaurant),
    )


@router.put(
    "/restaurants/{restaurant_id}",
    response_model=ApiResponse[AdminRestaurantResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def update_restaurant(
    restaurant_id: int,
    payload: AdminRestaurantUpdate,
    db: AsyncSession = Depends(get_db),
):
    restaurant = await _get_restaurant_or_404(db, restaurant_id)
    update_data = payload.model_dump(exclude_unset=True, exclude={"category_ids"})
    for field, value in update_data.items():
        setattr(restaurant, field, value)
    if payload.category_ids is not None:
        await _replace_restaurant_categories(db, restaurant, payload.category_ids)
    await db.commit()
    restaurant = await _get_restaurant_or_404(db, restaurant_id)
    return ApiResponse(
        message="Admin restaurant updated successfully.",
        data=_build_restaurant_response(restaurant),
    )


@router.delete(
    "/restaurants/{restaurant_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def delete_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    restaurant = await _get_restaurant_or_404(db, restaurant_id)
    await db.delete(restaurant)
    await db.commit()
    return ApiResponse(message="Admin restaurant deleted successfully.", data={"success": True})


@router.get(
    "/menu-items",
    response_model=ApiResponse[list[AdminMenuItemResponse]],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def list_menu_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MenuItem).order_by(MenuItem.id.desc()))
    items = [AdminMenuItemResponse.model_validate(item) for item in result.scalars().all()]
    return ApiResponse(message="Admin menu items fetched successfully.", data=items)


@router.post(
    "/menu-items",
    response_model=ApiResponse[AdminMenuItemResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def create_menu_item(payload: AdminMenuItemCreate, db: AsyncSession = Depends(get_db)):
    menu_item = MenuItem(**payload.model_dump())
    db.add(menu_item)
    await db.commit()
    await db.refresh(menu_item)
    return ApiResponse(
        message="Admin menu item created successfully.",
        data=AdminMenuItemResponse.model_validate(menu_item),
    )


@router.put(
    "/menu-items/{menu_item_id}",
    response_model=ApiResponse[AdminMenuItemResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def update_menu_item(
    menu_item_id: int,
    payload: AdminMenuItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    menu_item = await _get_menu_item_or_404(db, menu_item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(menu_item, field, value)
    await db.commit()
    await db.refresh(menu_item)
    return ApiResponse(
        message="Admin menu item updated successfully.",
        data=AdminMenuItemResponse.model_validate(menu_item),
    )


@router.delete(
    "/menu-items/{menu_item_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def delete_menu_item(menu_item_id: int, db: AsyncSession = Depends(get_db)):
    menu_item = await _get_menu_item_or_404(db, menu_item_id)
    await db.delete(menu_item)
    await db.commit()
    return ApiResponse(message="Admin menu item deleted successfully.", data={"success": True})


@router.get(
    "/promos",
    response_model=ApiResponse[list[AdminPromoResponse]],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def list_admin_promos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromoBanner).order_by(PromoBanner.sort_order.asc(), PromoBanner.id.desc()))
    items = [AdminPromoResponse.model_validate(item) for item in result.scalars().all()]
    return ApiResponse(message="Admin promos fetched successfully.", data=items)


@router.post(
    "/promos",
    response_model=ApiResponse[AdminPromoResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def create_promo(payload: AdminPromoCreate, db: AsyncSession = Depends(get_db)):
    promo = PromoBanner(**payload.model_dump())
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return ApiResponse(
        message="Admin promo created successfully.",
        data=AdminPromoResponse.model_validate(promo),
    )


@router.put(
    "/promos/{promo_id}",
    response_model=ApiResponse[AdminPromoResponse],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def update_promo(
    promo_id: int,
    payload: AdminPromoUpdate,
    db: AsyncSession = Depends(get_db),
):
    promo = await _get_promo_or_404(db, promo_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(promo, field, value)
    await db.commit()
    await db.refresh(promo)
    return ApiResponse(
        message="Admin promo updated successfully.",
        data=AdminPromoResponse.model_validate(promo),
    )


@router.delete(
    "/promos/{promo_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def delete_promo(promo_id: int, db: AsyncSession = Depends(get_db)):
    promo = await _get_promo_or_404(db, promo_id)
    await db.delete(promo)
    await db.commit()
    return ApiResponse(message="Admin promo deleted successfully.", data={"success": True})


@router.get(
    "/restaurants/{restaurant_id}/reservation-tables",
    response_model=ApiResponse[list[RestaurantTableSummary]],
)
async def list_admin_reservation_tables(
    restaurant_id: int,
    current_user: User = Depends(require_role(["super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.list_merchant_tables(current_user, restaurant_id)
    return ApiResponse(message="Admin reservation tables fetched successfully.", data=data)


@router.post(
    "/restaurants/{restaurant_id}/reservation-tables",
    response_model=ApiResponse[RestaurantTableSummary],
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_reservation_table(
    restaurant_id: int,
    payload: RestaurantTableCreateRequest,
    current_user: User = Depends(require_role(["super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.create_merchant_table(current_user, restaurant_id, payload)
    return ApiResponse(message="Admin reservation table created successfully.", data=data)


@router.put(
    "/restaurants/{restaurant_id}/reservation-tables/{table_id}",
    response_model=ApiResponse[RestaurantTableSummary],
)
async def update_admin_reservation_table(
    restaurant_id: int,
    table_id: int,
    payload: RestaurantTableUpdateRequest,
    current_user: User = Depends(require_role(["super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.update_merchant_table(current_user, restaurant_id, table_id, payload)
    return ApiResponse(message="Admin reservation table updated successfully.", data=data)


@router.delete(
    "/restaurants/{restaurant_id}/reservation-tables/{table_id}",
    response_model=ApiResponse[dict],
)
async def delete_admin_reservation_table(
    restaurant_id: int,
    table_id: int,
    current_user: User = Depends(require_role(["super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    await service.delete_merchant_table(current_user, restaurant_id, table_id)
    return ApiResponse(message="Admin reservation table deleted successfully.", data={"success": True})


@router.get(
    "/restaurants/{restaurant_id}/reservations",
    response_model=ApiResponse[list[ReservationResponse]],
)
async def list_admin_reservations(
    restaurant_id: int,
    reservation_date: date | None = Query(default=None),
    status_filter: ReservationStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(require_role(["super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.list_merchant_reservations(
        current_user,
        restaurant_id,
        reservation_date=reservation_date,
        status_filter=status_filter,
    )
    return ApiResponse(message="Admin reservations fetched successfully.", data=data)


@router.get(
    "/restaurants/{restaurant_id}/reservations/{reservation_id}",
    response_model=ApiResponse[ReservationResponse],
)
async def get_admin_reservation(
    restaurant_id: int,
    reservation_id: int,
    current_user: User = Depends(require_role(["super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.get_merchant_reservation(current_user, restaurant_id, reservation_id)
    return ApiResponse(message="Admin reservation fetched successfully.", data=data)


@router.post(
    "/restaurants/{restaurant_id}/reservations/{reservation_id}/status",
    response_model=ApiResponse[ReservationResponse],
)
async def update_admin_reservation_status(
    restaurant_id: int,
    reservation_id: int,
    payload: ReservationStatusUpdateRequest,
    current_user: User = Depends(require_role(["super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = ReservationService(db)
    data = await service.update_merchant_reservation_status(
        current_user,
        restaurant_id,
        reservation_id,
        payload,
    )
    return ApiResponse(message="Admin reservation updated successfully.", data=data)


@router.post(
    "/upload",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_role(["super_admin"]))],
)
async def upload_admin_file(
    file: UploadFile = File(...),
    folder: str = Form("general")
):
    try:
        url = await CloudinaryService.upload_image(file, folder)
        return ApiResponse(message="File uploaded successfully.", data={"url": url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
