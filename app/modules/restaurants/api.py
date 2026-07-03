from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.db.session import get_db
from app.modules.auth.deps import get_current_user_optional
from app.modules.restaurants.models import Category, Restaurant
from app.modules.restaurants.repository import RestaurantRepository
from app.modules.restaurants.schemas import (
    CategorySummary,
    HomeFeedResponse,
    HomeLocationContext,
    RestaurantCardSummary,
    RestaurantListResponse,
)
from app.schemas.common import ApiResponse

router = APIRouter(tags=["restaurants"])


def get_restaurant_repository(db=Depends(get_db)) -> RestaurantRepository:
    return RestaurantRepository(db)


def build_category_summary(category: Category) -> CategorySummary:
    return CategorySummary(
        id=category.id,
        slug=category.slug,
        name=category.name,
        icon_url=category.icon_url,
        sort_order=category.sort_order,
        is_featured=category.is_featured,
    )


def build_restaurant_summary(restaurant: Restaurant) -> RestaurantCardSummary:
    categories = [
        build_category_summary(link.category)
        for link in sorted(
            restaurant.category_links,
            key=lambda item: (item.category.sort_order, item.category.id),
        )
        if link.category.is_active
    ]
    return RestaurantCardSummary(
        id=restaurant.id,
        slug=restaurant.slug,
        name=restaurant.name,
        cover_image_url=restaurant.cover_image_url,
        logo_url=restaurant.logo_url,
        short_description=restaurant.short_description,
        primary_cuisine_label=restaurant.primary_cuisine_label,
        city=restaurant.city,
        area=restaurant.area,
        rating_average=restaurant.rating_average,
        review_count=restaurant.review_count,
        supports_delivery=restaurant.supports_delivery,
        has_free_delivery=restaurant.has_free_delivery,
        offer_text=restaurant.offer_text,
        delivery_eta_min_minutes=restaurant.delivery_eta_min_minutes,
        delivery_eta_max_minutes=restaurant.delivery_eta_max_minutes,
        is_featured=restaurant.is_featured,
        categories=categories,
    )


@router.get("/restaurants", response_model=ApiResponse[RestaurantListResponse])
async def list_restaurants(
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    restaurants = await repo.list_restaurants()
    total = await repo.count_restaurants()
    data = RestaurantListResponse(
        items=[build_restaurant_summary(restaurant) for restaurant in restaurants],
        total=total,
    )
    return ApiResponse(message="Restaurants fetched successfully.", data=data)


from app.modules.auth.models import User
from app.modules.customers.service import CustomerService
from app.modules.catalog.service import CatalogService
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.merchandising.service import MerchandisingService
from app.modules.merchandising.models import PromoPlacement
from app.modules.merchandising.schemas import PromoBannerResponse

@router.get("/home/feed", response_model=ApiResponse[HomeFeedResponse])
async def get_home_feed(
    repo: RestaurantRepository = Depends(get_restaurant_repository),
    db=Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
):
    restaurants = await repo.list_restaurants()
    categories = await repo.list_featured_categories()

    location_title = "Choose location"
    location_subtitle = "Set delivery address to personalize restaurants"
    selected_address_id = None
    saved_addresses_count = 0
    selected_address_label = None

    if current_user is not None:
        customer_service = CustomerService(db)
        profile = await customer_service.get_profile(current_user.id)
        saved_addresses_count = profile.saved_addresses_count
        if profile.default_address is not None:
            location_title = profile.default_address.location_title
            location_subtitle = profile.default_address.location_subtitle
            selected_address_id = profile.default_address.id
            selected_address_label = profile.default_address.address_summary
    elif latitude is not None and longitude is not None:
        location_title = "Delivery area selected"
        location_subtitle = f"Near {latitude:.4f}, {longitude:.4f}"

    catalog_service = CatalogService(db)
    raw_recommended = await catalog_service.repository.list_featured_items(limit=8)
    raw_popular = await catalog_service.repository.list_popular_items(limit=8)
    
    recommended_items = [MenuItemSummary.model_validate(item) for item in raw_recommended]
    popular_foods = [MenuItemSummary.model_validate(item) for item in raw_popular]
    
    # Fetch promos
    merch_service = MerchandisingService(db)
    promos = await merch_service.list_active_promos(PromoPlacement.home_carousel)
            
    data = HomeFeedResponse(
        location_context=HomeLocationContext(
            location_title=location_title,
            location_subtitle=location_subtitle,
            selected_address_id=selected_address_id,
            saved_addresses_count=saved_addresses_count,
            selected_address_label=selected_address_label,
        ),
        categories=[build_category_summary(category) for category in categories],
        restaurants=[build_restaurant_summary(restaurant) for restaurant in restaurants],
        promos=promos,
        recommended_items=recommended_items,
        popular_foods=popular_foods,
    )
    return ApiResponse(message="Home feed fetched successfully.", data=data)
