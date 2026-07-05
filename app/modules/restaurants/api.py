from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.session import get_db
from app.modules.auth.deps import get_current_user_optional
from app.modules.auth.models import User
from app.modules.catalog.models import FoodType
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.catalog.service import CatalogService
from app.modules.customers.service import CustomerService
from app.modules.merchandising.models import PromoPlacement
from app.modules.merchandising.service import MerchandisingService
from app.modules.restaurants.models import Category, Restaurant
from app.modules.restaurants.repository import RestaurantRepository
from app.modules.restaurants.schemas import (
    CategorySummary,
    HomeFeedResponse,
    HomeLocationContext,
    RestaurantDetailResponse,
    RestaurantMenuSection,
    RestaurantReviewResponse,
    RestaurantReviewSummary,
    RestaurantCardSummary,
    RestaurantListResponse,
    RestaurantSearchMatch,
    RestaurantSearchResponse,
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
    return build_restaurant_summary_with_context(restaurant=restaurant, latitude=None, longitude=None)


def _compute_distance_km(
    *,
    restaurant: Restaurant,
    latitude: float | None,
    longitude: float | None,
) -> float | None:
    if (
        latitude is None
        or longitude is None
        or restaurant.latitude is None
        or restaurant.longitude is None
    ):
        return None

    earth_radius_km = 6371.0
    d_lat = radians(restaurant.latitude - latitude)
    d_lon = radians(restaurant.longitude - longitude)
    origin_lat = radians(latitude)
    target_lat = radians(restaurant.latitude)

    hav = sin(d_lat / 2) ** 2 + cos(origin_lat) * cos(target_lat) * sin(d_lon / 2) ** 2
    return round(2 * earth_radius_km * asin(sqrt(hav)), 2)


def _is_open_now(restaurant: Restaurant) -> bool | None:
    if not restaurant.opening_time or not restaurant.closing_time:
        return None

    try:
        opening = datetime.strptime(restaurant.opening_time, "%H:%M").time()
        closing = datetime.strptime(restaurant.closing_time, "%H:%M").time()
        now = datetime.utcnow().time()
        if opening <= closing:
            return opening <= now <= closing
        return now >= opening or now <= closing
    except ValueError:
        return None


def _parse_facilities(restaurant: Restaurant) -> list[str]:
    raw = restaurant.facilities_text or ""
    if not raw.strip():
        return []
    separators = raw.replace("\n", ",").split(",")
    return [item.strip() for item in separators if item.strip()]


def build_restaurant_summary_with_context(
    *,
    restaurant: Restaurant,
    latitude: float | None,
    longitude: float | None,
) -> RestaurantCardSummary:
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
        supports_pickup=restaurant.supports_pickup,
        supports_table_booking=restaurant.supports_table_booking,
        offer_text=restaurant.offer_text,
        contact_phone=restaurant.contact_phone,
        contact_email=restaurant.contact_email,
        delivery_eta_min_minutes=restaurant.delivery_eta_min_minutes,
        delivery_eta_max_minutes=restaurant.delivery_eta_max_minutes,
        opening_time=restaurant.opening_time,
        closing_time=restaurant.closing_time,
        is_open_now=_is_open_now(restaurant),
        distance_km=_compute_distance_km(
            restaurant=restaurant,
            latitude=latitude,
            longitude=longitude,
        ),
        is_featured=restaurant.is_featured,
        categories=categories,
    )


@router.get(
    "/restaurants",
    response_model=ApiResponse[RestaurantListResponse],
    summary="List customer-visible restaurants",
    description=(
        "Returns the active restaurant cards used by the YummyDoors customer surfaces. "
        "Each restaurant includes delivery metadata, cuisine labels, and category links."
    ),
)
async def list_restaurants(
    q: str | None = Query(default=None, description="Search restaurants and menu items by text."),
    category_slug: str | None = Query(default=None, description="Filter by category slug."),
    food_type: FoodType | None = Query(default=None, description="Filter menu-bearing restaurants by food type."),
    supports_delivery: bool | None = Query(default=None),
    supports_pickup: bool | None = Query(default=None),
    has_free_delivery: bool | None = Query(default=None),
    featured_only: bool | None = Query(default=None),
    open_now: bool | None = Query(default=None, description="Filter restaurants that are currently open."),
    sort_by: str | None = Query(default=None, description="Sort by recommended, rating, delivery_time, or highly_reordered."),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    restaurants = await repo.list_restaurants(
        search=q,
        category_slug=category_slug,
        food_type=food_type,
        supports_delivery=supports_delivery,
        supports_pickup=supports_pickup,
        has_free_delivery=has_free_delivery,
        featured_only=featured_only,
        sort_by=sort_by,
    )
    if open_now is not None:
        restaurants = [
            restaurant
            for restaurant in restaurants
            if _is_open_now(restaurant) is open_now
        ]
    total = len(restaurants)
    data = RestaurantListResponse(
        items=[
            build_restaurant_summary_with_context(
                restaurant=restaurant,
                latitude=latitude,
                longitude=longitude,
            )
            for restaurant in restaurants
        ],
        total=total,
    )
    return ApiResponse(message="Restaurants fetched successfully.", data=data)


@router.get(
    "/restaurants/{slug}",
    response_model=ApiResponse[RestaurantDetailResponse],
    summary="Get restaurant detail feed",
    description=(
        "Returns a single restaurant with grouped menu sections, featured items, "
        "popular items, and related restaurants for the detail screen."
    ),
    responses={
        404: {"description": "Restaurant not found."},
    },
)
async def get_restaurant_detail(
    slug: str,
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
    db=Depends(get_db),
):
    restaurant = await repo.get_restaurant_by_slug(slug)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")

    catalog_repo = CatalogRepository(db)
    menu_items = await catalog_repo.get_menu_by_restaurant(restaurant.id)
    featured_items = await catalog_repo.list_featured_items_by_restaurant(restaurant.id)
    popular_items = await catalog_repo.list_popular_items_by_restaurant(restaurant.id)
    related_restaurants = await repo.list_related_restaurants(restaurant)
    reviews = await repo.list_reviews(restaurant.id)

    grouped_sections: OrderedDict[tuple[int | None, str | None, str], list[MenuItemSummary]] = OrderedDict()
    for item in menu_items:
        category = item.category
        key = (
            category.id if category else None,
            category.slug if category else None,
            category.name if category else "More from this restaurant",
        )
        grouped_sections.setdefault(key, []).append(MenuItemSummary.model_validate(item))

    menu_sections = [
        RestaurantMenuSection(
            category_id=category_id,
            category_slug=category_slug,
            category_name=category_name,
            items=items,
        )
        for (category_id, category_slug, category_name), items in grouped_sections.items()
    ]

    data = RestaurantDetailResponse(
        restaurant=build_restaurant_summary_with_context(
            restaurant=restaurant,
            latitude=latitude,
            longitude=longitude,
        ),
        menu_sections=menu_sections,
        featured_items=[MenuItemSummary.model_validate(item) for item in featured_items],
        popular_items=[MenuItemSummary.model_validate(item) for item in popular_items],
        related_restaurants=[
            build_restaurant_summary_with_context(
                restaurant=item,
                latitude=latitude,
                longitude=longitude,
            )
            for item in related_restaurants
        ],
        about_text=restaurant.about_text,
        facilities=_parse_facilities(restaurant),
        reviews_summary=RestaurantReviewSummary(
            average_rating=restaurant.rating_average,
            total_reviews=restaurant.review_count,
            highlights=[review.comment for review in reviews[:3] if review.comment],
        ),
        reviews=[
            RestaurantReviewResponse(
                id=review.id,
                author_name=review.author_name,
                rating=review.rating,
                comment=review.comment,
                source=review.source,
                created_at=review.created_at.isoformat(),
            )
            for review in reviews
        ],
    )
    return ApiResponse(message="Restaurant detail fetched successfully.", data=data)


@router.get(
    "/search",
    response_model=ApiResponse[RestaurantSearchResponse],
    summary="Search restaurants and menu items",
)
async def search_restaurants(
    q: str = Query(..., min_length=1, description="Search text for restaurants or menu items."),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    matches = await repo.search_restaurants(query=q)
    data = RestaurantSearchResponse(
        items=[
            RestaurantSearchMatch(
                restaurant=build_restaurant_summary_with_context(
                    restaurant=restaurant,
                    latitude=latitude,
                    longitude=longitude,
                ),
                matched_menu_items=[MenuItemSummary.model_validate(item) for item in matched_items],
            )
            for restaurant, matched_items in matches
        ],
        total=len(matches),
    )
    return ApiResponse(message="Search results fetched successfully.", data=data)


@router.get(
    "/restaurants/{slug}/reviews",
    response_model=ApiResponse[list[RestaurantReviewResponse]],
    summary="List published restaurant reviews",
)
async def list_restaurant_reviews(
    slug: str,
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    restaurant = await repo.get_restaurant_by_slug(slug)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")

    reviews = await repo.list_reviews(restaurant.id)
    data = [
        RestaurantReviewResponse(
            id=review.id,
            author_name=review.author_name,
            rating=review.rating,
            comment=review.comment,
            source=review.source,
            created_at=review.created_at.isoformat(),
        )
        for review in reviews
    ]
    return ApiResponse(message="Restaurant reviews fetched successfully.", data=data)

@router.get(
    "/home/feed",
    response_model=ApiResponse[HomeFeedResponse],
    summary="Get homepage feed",
    description=(
        "Builds the customer homepage payload used by YummyDoors surfaces. "
        "The response includes location context, featured categories, promo banners, "
        "recommended items, popular foods, and restaurant cards."
    ),
)
async def get_home_feed(
    repo: RestaurantRepository = Depends(get_restaurant_repository),
    db=Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    latitude: float | None = Query(
        default=None,
        description="Optional latitude used for guest location context before an address is saved.",
    ),
    longitude: float | None = Query(
        default=None,
        description="Optional longitude used for guest location context before an address is saved.",
    ),
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
        location_title = "Current Location"
        location_subtitle = "Delivering to your area"

    catalog_service = CatalogService(db)
    raw_recommended = await catalog_service.repository.list_featured_items(limit=8)
    raw_popular = await catalog_service.repository.list_popular_items(limit=8)
    
    recommended_items = [MenuItemSummary.model_validate(item) for item in raw_recommended]
    popular_foods = [MenuItemSummary.model_validate(item) for item in raw_popular]
    
    merch_service = MerchandisingService(db)
    hero_promos = await merch_service.list_active_promos(PromoPlacement.home_carousel)
    banner_promos = await merch_service.list_active_promos(PromoPlacement.home_banner)
    promos = hero_promos if hero_promos else banner_promos

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
        hero_promos=hero_promos,
        banner_promos=banner_promos,
        recommended_items=recommended_items,
        popular_foods=popular_foods,
    )
    return ApiResponse(message="Home feed fetched successfully.", data=data)
