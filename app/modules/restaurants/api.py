from __future__ import annotations

import logging
from collections import OrderedDict
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, get_current_user_optional
from app.modules.auth.models import User
from app.modules.catalog.models import FoodType
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.catalog.service import CatalogService
from app.modules.customers.service import CustomerService
from app.modules.favorites.repository import FavoritesRepository
from app.modules.merchandising.models import PromoPlacement
from app.modules.merchandising.service import MerchandisingService
from app.modules.restaurants.models import Category, Restaurant
from app.modules.restaurants.repository import RestaurantRepository
from app.modules.restaurants.schemas import (
    CategorySummary,
    DashboardStatPoint,
    DashboardStatsResponse,
    GalleryImageCreate,
    GalleryImageResponse,
    HomeFeedFilterOption,
    HomeFeedResponse,
    HomeLocationContext,
    RestaurantCardSummary,
    RestaurantDetailResponse,
    RestaurantListResponse,
    RestaurantMenuSection,
    RestaurantReviewCreate,
    RestaurantReviewEligibilityResponse,
    RestaurantReviewResponse,
    RestaurantReviewSummary,
    RestaurantReviewUpdate,
    RestaurantSearchMatch,
    RestaurantSearchResponse,
    TopSellingItem,
)
from app.schemas.common import ApiResponse

router = APIRouter(tags=["restaurants"])
logger = logging.getLogger(__name__)


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
    return build_restaurant_summary_with_context(
        restaurant=restaurant, latitude=None, longitude=None
    )


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
        latitude=restaurant.latitude,
        longitude=restaurant.longitude,
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


def build_review_response(
    review,
    *,
    current_user_id: int | None,
) -> RestaurantReviewResponse:
    is_mine = current_user_id is not None and review.user_id == current_user_id
    image_urls = [img.image_url for img in sorted(review.images, key=lambda i: i.sort_order)] if hasattr(review, "images") and review.images else []
    return RestaurantReviewResponse(
        id=review.id,
        user_id=review.user_id,
        author_name=review.author_name,
        rating=review.rating,
        comment=review.comment,
        source=review.source,
        created_at=review.created_at.isoformat(),
        is_mine=is_mine,
        can_edit=is_mine,
        image_urls=image_urls,
    )


def build_review_eligibility(
    *,
    has_delivered_order: bool,
    existing_review_id: int | None,
    can_review: bool = False,
    unreviewed_order_id: int | None = None,
) -> RestaurantReviewEligibilityResponse:
    if can_review:
        return RestaurantReviewEligibilityResponse(
            can_create_review=True,
            existing_review_id=None,
            reason=None,
        )
    if existing_review_id is not None:
        return RestaurantReviewEligibilityResponse(
            can_create_review=False,
            existing_review_id=existing_review_id,
            reason="You already reviewed this restaurant. Edit your existing review instead.",
        )
    if not has_delivered_order:
        return RestaurantReviewEligibilityResponse(
            can_create_review=False,
            reason="Only customers with delivered orders can review this restaurant.",
        )
    return RestaurantReviewEligibilityResponse(
        can_create_review=False,
        reason="You have no unreviewed orders for this restaurant."
    )


def build_home_feed_filters() -> list[HomeFeedFilterOption]:
    return [
        HomeFeedFilterOption(key="filters", label="Filters", type="sheet"),
        HomeFeedFilterOption(
            key="sort_by",
            label="Sort By",
            type="sort",
            query_param="sort_by",
        ),
        HomeFeedFilterOption(
            key="highly_reordered",
            label="Highly Reordered",
            query_param="sort_by",
            value="highly_reordered",
        ),
        HomeFeedFilterOption(
            key="veg",
            label="Veg",
            query_param="food_type",
            value=FoodType.veg.value,
        ),
        HomeFeedFilterOption(
            key="non_veg",
            label="Non Veg",
            query_param="food_type",
            value=FoodType.non_veg.value,
        ),
    ]


def build_safe_menu_item_summaries(items: list, *, section: str) -> list[MenuItemSummary]:
    summaries: list[MenuItemSummary] = []
    for item in items:
        try:
            summaries.append(MenuItemSummary.model_validate(item))
        except ValidationError as exc:
            logger.warning(
                "Skipping invalid menu item in home feed section %s: %s",
                section,
                exc,
            )
    return summaries


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
    food_type: FoodType | None = Query(
        default=None, description="Filter menu-bearing restaurants by food type."
    ),
    supports_delivery: bool | None = Query(default=None),
    supports_pickup: bool | None = Query(default=None),
    has_free_delivery: bool | None = Query(default=None),
    featured_only: bool | None = Query(default=None),
    open_now: bool | None = Query(
        default=None, description="Filter restaurants that are currently open."
    ),
    sort_by: str | None = Query(
        default=None,
        description="Sort by recommended, rating, delivery_time, highly_reordered, or distance.",
    ),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    current_user: User | None = Depends(get_current_user_optional),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
    db=Depends(get_db),
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
            restaurant for restaurant in restaurants if _is_open_now(restaurant) is open_now
        ]

    if sort_by == "distance" and latitude is not None and longitude is not None:
        restaurants.sort(
            key=lambda r: (
                _compute_distance_km(restaurant=r, latitude=latitude, longitude=longitude)
                or 999999.0
            )
        )
    favorite_restaurant_ids: set[int] = set()
    if current_user is not None:
        favorite_restaurant_ids = await FavoritesRepository(db).list_favorite_restaurant_ids(
            current_user.id
        )
    total = len(restaurants)
    data = RestaurantListResponse(
        items=[
            build_restaurant_summary_with_context(
                restaurant=restaurant,
                latitude=latitude,
                longitude=longitude,
            ).model_copy(update={"is_favorited": restaurant.id in favorite_restaurant_ids})
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
    current_user: User | None = Depends(get_current_user_optional),
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
    favorite_restaurant_ids: set[int] = set()
    favorite_menu_item_ids: set[int] = set()
    viewer_review = None
    review_eligibility = None
    if current_user is not None:
        favorites_repo = FavoritesRepository(db)
        favorite_restaurant_ids = await favorites_repo.list_favorite_restaurant_ids(current_user.id)
        favorite_menu_item_ids = await favorites_repo.list_favorite_menu_item_ids(current_user.id)
        has_delivered_order = await repo.has_delivered_order(restaurant.id, current_user.id)
        unreviewed_order_id = await repo.get_unreviewed_delivered_order_id(restaurant.id, current_user.id)
        
        can_review = unreviewed_order_id is not None
        viewer_review_model = None if can_review else await repo.get_review_by_user(restaurant.id, current_user.id)

        viewer_review = (
            build_review_response(viewer_review_model, current_user_id=current_user.id)
            if viewer_review_model is not None
            else None
        )
        review_eligibility = build_review_eligibility(
            has_delivered_order=has_delivered_order,
            existing_review_id=viewer_review_model.id if viewer_review_model is not None else None,
            can_review=can_review,
            unreviewed_order_id=unreviewed_order_id,
        )

    grouped_sections: OrderedDict[tuple[int | None, str | None, str], list[MenuItemSummary]] = (
        OrderedDict()
    )
    for item in menu_items:
        category = item.category
        key = (
            category.id if category else None,
            category.slug if category else None,
            category.name if category else "More from this restaurant",
        )
        grouped_sections.setdefault(key, []).append(
            MenuItemSummary.model_validate(item).model_copy(
                update={"is_favorited": item.id in favorite_menu_item_ids}
            )
        )

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
        ).model_copy(update={"is_favorited": restaurant.id in favorite_restaurant_ids}),
        menu_sections=menu_sections,
        featured_items=[
            MenuItemSummary.model_validate(item).model_copy(
                update={"is_favorited": item.id in favorite_menu_item_ids}
            )
            for item in featured_items
        ],
        popular_items=[
            MenuItemSummary.model_validate(item).model_copy(
                update={"is_favorited": item.id in favorite_menu_item_ids}
            )
            for item in popular_items
        ],
        related_restaurants=[
            build_restaurant_summary_with_context(
                restaurant=item,
                latitude=latitude,
                longitude=longitude,
            ).model_copy(update={"is_favorited": item.id in favorite_restaurant_ids})
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
            build_review_response(review, current_user_id=current_user.id if current_user else None)
            for review in reviews
        ],
        viewer_review=viewer_review,
        review_eligibility=review_eligibility,
        gallery_images=[
            GalleryImageResponse(id=img.id, image_url=img.image_url, caption=img.caption, sort_order=img.sort_order)
            for img in restaurant.gallery_images
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
    current_user: User | None = Depends(get_current_user_optional),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
    db=Depends(get_db),
):
    matches = await repo.search_restaurants(query=q)
    favorite_restaurant_ids: set[int] = set()
    favorite_menu_item_ids: set[int] = set()
    if current_user is not None:
        favorites_repo = FavoritesRepository(db)
        favorite_restaurant_ids = await favorites_repo.list_favorite_restaurant_ids(current_user.id)
        favorite_menu_item_ids = await favorites_repo.list_favorite_menu_item_ids(current_user.id)
    data = RestaurantSearchResponse(
        items=[
            RestaurantSearchMatch(
                restaurant=build_restaurant_summary_with_context(
                    restaurant=restaurant,
                    latitude=latitude,
                    longitude=longitude,
                ).model_copy(update={"is_favorited": restaurant.id in favorite_restaurant_ids}),
                matched_menu_items=[
                    MenuItemSummary.model_validate(item).model_copy(
                        update={"is_favorited": item.id in favorite_menu_item_ids}
                    )
                    for item in matched_items
                ],
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
    current_user: User | None = Depends(get_current_user_optional),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    restaurant = await repo.get_restaurant_by_slug(slug)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")

    reviews = await repo.list_reviews(restaurant.id)
    data = [
        build_review_response(review, current_user_id=current_user.id if current_user else None)
        for review in reviews
    ]
    return ApiResponse(message="Restaurant reviews fetched successfully.", data=data)


@router.get(
    "/restaurants/{slug}/review-eligibility",
    response_model=ApiResponse[RestaurantReviewEligibilityResponse],
    summary="Check whether the current customer can write a review",
)
async def get_restaurant_review_eligibility(
    slug: str,
    current_user: User | None = Depends(get_current_user_optional),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )

    restaurant = await repo.get_restaurant_by_slug(slug)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")

    has_delivered_order = await repo.has_delivered_order(restaurant.id, current_user.id)
    unreviewed_order_id = await repo.get_unreviewed_delivered_order_id(restaurant.id, current_user.id)
    can_review = unreviewed_order_id is not None
    existing_review = None if can_review else await repo.get_review_by_user(restaurant.id, current_user.id)
    
    data = build_review_eligibility(
        has_delivered_order=has_delivered_order,
        existing_review_id=existing_review.id if existing_review is not None else None,
        can_review=can_review,
        unreviewed_order_id=unreviewed_order_id,
    )
    return ApiResponse(message="Review eligibility fetched successfully.", data=data)


@router.post(
    "/restaurants/{slug}/reviews",
    response_model=ApiResponse[RestaurantReviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a restaurant review",
)
async def create_restaurant_review(
    slug: str,
    payload: RestaurantReviewCreate,
    current_user: User | None = Depends(get_current_user_optional),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5."
        )

    restaurant = await repo.get_restaurant_by_slug(slug)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")


    unreviewed_order_id = await repo.get_unreviewed_delivered_order_id(restaurant.id, current_user.id)

    # If they are trying to review a specific order, check that order directly
    if payload.order_id is not None:
        order_review = await repo.get_review_by_order(payload.order_id)
        if order_review is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This order has already been reviewed.",
            )
        # Verify the order belongs to them and is delivered
        from app.modules.orders.models import Order, OrderStatus
        order = await repo.db.get(Order, payload.order_id)
        if not order or order.customer_id != current_user.id or order.status != OrderStatus.delivered:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or undelivered order.",
            )
        target_order_id = payload.order_id
    else:
        # Otherwise, fall back to any unreviewed order
        if unreviewed_order_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have no remaining unreviewed orders for this restaurant.",
            )
        target_order_id = unreviewed_order_id

    review = await repo.create_review(
        restaurant_id=restaurant.id,
        user_id=current_user.id,
        author_name=current_user.full_name,
        rating=payload.rating,
        comment=payload.comment.strip() if payload.comment else None,
        order_id=target_order_id,
        image_urls=payload.image_urls or [],
    )
    await repo.sync_review_stats(restaurant.id)
    data = build_review_response(review, current_user_id=current_user.id)
    return ApiResponse(message="Review created successfully.", data=data)


@router.patch(
    "/restaurants/{slug}/reviews/{review_id}",
    response_model=ApiResponse[RestaurantReviewResponse],
    summary="Edit my restaurant review",
)
async def update_restaurant_review(
    slug: str,
    review_id: int,
    payload: RestaurantReviewUpdate,
    current_user: User | None = Depends(get_current_user_optional),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    if payload.rating is not None and not 1 <= payload.rating <= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5."
        )

    restaurant = await repo.get_restaurant_by_slug(slug)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")

    review = await repo.get_review_by_id(restaurant.id, review_id)
    if review is None or review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")

    updated = await repo.update_review(
        review,
        rating=payload.rating,
        comment=payload.comment.strip() if payload.comment is not None else None,
        image_urls=payload.image_urls,
    )
    await repo.sync_review_stats(restaurant.id)
    data = build_review_response(updated, current_user_id=current_user.id)
    return ApiResponse(message="Review updated successfully.", data=data)


@router.delete(
    "/restaurants/{slug}/reviews/{review_id}",
    response_model=ApiResponse[dict],
    summary="Delete my restaurant review",
)
async def delete_restaurant_review(
    slug: str,
    review_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )

    restaurant = await repo.get_restaurant_by_slug(slug)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")

    review = await repo.get_review_by_id(restaurant.id, review_id)
    if review is None or review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")

    await repo.delete_review(review)
    await repo.sync_review_stats(restaurant.id)
    return ApiResponse(message="Review deleted successfully.", data={"review_id": review_id})


# ── Gallery Endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/restaurants/{slug}/gallery",
    response_model=ApiResponse[list[GalleryImageResponse]],
    summary="List restaurant gallery images",
)
async def list_restaurant_gallery(
    slug: str,
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    restaurant = await repo.get_restaurant_by_slug(slug)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
    images = await repo.list_gallery_images(restaurant.id)
    data = [
        GalleryImageResponse(id=img.id, image_url=img.image_url, caption=img.caption, sort_order=img.sort_order)
        for img in images
    ]
    return ApiResponse(message="Gallery images fetched successfully.", data=data)


@router.post(
    "/merchant/restaurants/{restaurant_id}/gallery",
    response_model=ApiResponse[GalleryImageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add a gallery image (merchant)",
)
async def add_merchant_gallery_image(
    restaurant_id: int,
    payload: GalleryImageCreate,
    current_user: User = Depends(get_current_user),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    restaurant = await repo.get_restaurant_by_id(restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
    existing = await repo.list_gallery_images(restaurant_id)
    if len(existing) >= 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gallery limit reached (max 20 images).",
        )
    image = await repo.add_gallery_image(
        restaurant_id=restaurant_id,
        image_url=payload.image_url,
        caption=payload.caption,
        sort_order=payload.sort_order,
    )
    data = GalleryImageResponse(id=image.id, image_url=image.image_url, caption=image.caption, sort_order=image.sort_order)
    return ApiResponse(message="Gallery image added successfully.", data=data)


@router.get(
    "/merchant/restaurants/{restaurant_id}/gallery",
    response_model=ApiResponse[list[GalleryImageResponse]],
    summary="List merchant restaurant gallery images",
)
async def list_merchant_gallery_images(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    images = await repo.list_gallery_images(restaurant_id)
    data = [
        GalleryImageResponse(id=img.id, image_url=img.image_url, caption=img.caption, sort_order=img.sort_order)
        for img in images
    ]
    return ApiResponse(message="Gallery images fetched successfully.", data=data)


@router.delete(
    "/merchant/restaurants/{restaurant_id}/gallery/{image_id}",
    response_model=ApiResponse[dict],
    summary="Delete a gallery image (merchant)",
)
async def delete_merchant_gallery_image(
    restaurant_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    repo: RestaurantRepository = Depends(get_restaurant_repository),
):
    image = await repo.get_gallery_image_by_id(restaurant_id, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery image not found.")
    await repo.delete_gallery_image(image)
    return ApiResponse(message="Gallery image deleted successfully.", data={"image_id": image_id})


@router.get(
    "/home/feed",
    response_model=ApiResponse[HomeFeedResponse],
    summary="Get homepage feed",
    description=(
        "Builds the customer homepage payload used by YummyDoors surfaces. "
        "The response includes location context, featured categories, filter chips, "
        "promo banners, recommended items, sales-ranked popular foods, featured videos, "
        "and restaurant cards."
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
    explore_restaurants = await repo.list_popular_restaurants(limit=12)
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
            latitude = profile.default_address.latitude
            longitude = profile.default_address.longitude
    elif latitude is not None and longitude is not None:
        location_title = "Current Location"
        location_subtitle = "Delivering to your area"

    catalog_service = CatalogService(db)
    raw_popular = await catalog_service.repository.list_popular_items(limit=8)
    popular_foods = build_safe_menu_item_summaries(
        list(raw_popular),
        section="popular_foods",
    )

    # Recommended for you: pull items from favorited restaurants; fall back to featured items
    if current_user is not None:
        fav_repo = FavoritesRepository(db)
        fav_restaurant_ids = list(await fav_repo.list_favorite_restaurant_ids(current_user.id))
        if fav_restaurant_ids:
            raw_recommended = await catalog_service.repository.list_items_by_restaurants(
                fav_restaurant_ids, limit=8
            )
        else:
            raw_recommended = await catalog_service.repository.list_featured_items(limit=8)
    else:
        raw_recommended = await catalog_service.repository.list_featured_items(limit=8)
    recommended_items = build_safe_menu_item_summaries(
        list(raw_recommended),
        section="recommended_items",
    )

    merch_service = MerchandisingService(db)
    hero_promos = await merch_service.list_active_promos(
        PromoPlacement.home_carousel, global_only=True
    )
    banner_promos = await merch_service.list_active_promos(
        PromoPlacement.home_banner, global_only=True
    )
    promos = hero_promos if hero_promos else banner_promos
    featured_videos = await merch_service.list_active_featured_videos(limit=8)

    data = HomeFeedResponse(
        location_context=HomeLocationContext(
            location_title=location_title,
            location_subtitle=location_subtitle,
            selected_address_id=selected_address_id,
            saved_addresses_count=saved_addresses_count,
            selected_address_label=selected_address_label,
            latitude=latitude,
            longitude=longitude,
        ),
        categories=[build_category_summary(category) for category in categories],
        restaurants=[build_restaurant_summary(restaurant) for restaurant in restaurants],
        explore_restaurants=[build_restaurant_summary(r) for r in explore_restaurants],
        filters=build_home_feed_filters(),
        promos=promos,
        hero_promos=hero_promos,
        banner_promos=banner_promos,
        recommended_items=recommended_items,
        popular_foods=popular_foods,
        featured_videos=featured_videos,
    )
    return ApiResponse(message="Home feed fetched successfully.", data=data)


@router.get(
    "/merchant/restaurants/me/stats",
    response_model=DashboardStatsResponse,
    summary="Merchant dashboard analytics",
    description=(
        "Returns aggregated stats for the merchant's active restaurant: "
        "order counts, revenue, reviews, messages, bookmarks, and time-series data "
        "for charts."
    ),
)
async def get_merchant_stats(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.favorites.models import UserFavoriteRestaurant
    from app.modules.messages.repository import MessageRepository
    from app.modules.orders.models import Order, OrderItem, OrderStatus
    from app.modules.reviews.repository import ReviewRepository
    from app.modules.workspaces.repository import WorkspaceRepository

    # ── workspace check ──────────────────────────────────────────────────────
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_active_workspace(current_user.id)
    if not workspace or workspace.workspace_type != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active workspace is not a merchant workspace.",
        )
    restaurant_id = workspace.primary_restaurant_id
    if not restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active restaurant in this workspace.",
        )

    now_utc = datetime.now(UTC)
    cutoff_7d = now_utc - timedelta(days=7)
    cutoff_14d = now_utc - timedelta(days=14)
    cutoff_30d = now_utc - timedelta(days=30)

    # ── new orders last 7d ───────────────────────────────────────────────────
    stmt_new_orders_7d = select(func.count()).where(
        Order.restaurant_id == restaurant_id,
        Order.status != OrderStatus.cancelled,
        Order.created_at >= cutoff_7d,
    )
    new_orders_7d: int = (await db.execute(stmt_new_orders_7d)).scalar_one()

    # ── revenue last 7d ──────────────────────────────────────────────────────
    stmt_revenue_7d = select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
        Order.restaurant_id == restaurant_id,
        Order.status == OrderStatus.delivered,
        Order.created_at >= cutoff_7d,
    )
    total_revenue_7d: float = float((await db.execute(stmt_revenue_7d)).scalar_one())

    avg_order_value: float = round(total_revenue_7d / new_orders_7d, 2) if new_orders_7d else 0.0

    # ── revenue last 30d ─────────────────────────────────────────────────────
    stmt_revenue_30d = select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
        Order.restaurant_id == restaurant_id,
        Order.status == OrderStatus.delivered,
        Order.created_at >= cutoff_30d,
    )
    total_revenue_30d: float = float((await db.execute(stmt_revenue_30d)).scalar_one())

    stmt_total_orders_30d = select(func.count()).where(
        Order.restaurant_id == restaurant_id,
        Order.status != OrderStatus.cancelled,
        Order.created_at >= cutoff_30d,
    )
    total_orders_30d: int = (await db.execute(stmt_total_orders_30d)).scalar_one()

    # ── unread messages ───────────────────────────────────────────────────────
    msg_repo = MessageRepository(db)
    unread_messages = await msg_repo.total_unread_for_restaurant(restaurant_id)

    # ── new reviews last 7d ───────────────────────────────────────────────────
    review_repo = ReviewRepository(db)
    new_reviews_7d = await review_repo.count_new_reviews(restaurant_id, since_days=7)

    # ── new bookmarks last 7d ────────────────────────────────────────────────
    stmt_bookmarks = select(func.count()).where(
        UserFavoriteRestaurant.restaurant_id == restaurant_id,
        UserFavoriteRestaurant.created_at >= cutoff_7d,
    )
    new_bookmarks_7d: int = (await db.execute(stmt_bookmarks)).scalar_one()

    # ── time-series: order volume & revenue last 14 days ─────────────────────
    stmt_14d = (
        select(
            func.date(Order.created_at).label("day"),
            func.count().label("cnt"),
            func.coalesce(func.sum(Order.total_price), 0.0).label("rev"),
        )
        .where(
            Order.restaurant_id == restaurant_id,
            Order.status != OrderStatus.cancelled,
            Order.created_at >= cutoff_14d,
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    rows_14d = (await db.execute(stmt_14d)).all()
    order_volume_14d = [
        DashboardStatPoint(date=str(row.day), count=row.cnt, revenue=float(row.rev))
        for row in rows_14d
    ]

    # ── time-series: daily revenue last 30 days ──────────────────────────────
    stmt_30d = (
        select(
            func.date(Order.created_at).label("day"),
            func.count().label("cnt"),
            func.coalesce(func.sum(Order.total_price), 0.0).label("rev"),
        )
        .where(
            Order.restaurant_id == restaurant_id,
            Order.status == OrderStatus.delivered,
            Order.created_at >= cutoff_30d,
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    rows_30d = (await db.execute(stmt_30d)).all()
    daily_revenue_30d = [
        DashboardStatPoint(date=str(row.day), count=row.cnt, revenue=float(row.rev))
        for row in rows_30d
    ]

    # ── top-selling menu items last 30 days ───────────────────────────────────
    stmt_top = (
        select(OrderItem.name, func.sum(OrderItem.quantity).label("total_qty"))
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.restaurant_id == restaurant_id,
            Order.status != OrderStatus.cancelled,
            Order.created_at >= cutoff_30d,
        )
        .group_by(OrderItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    top_rows = (await db.execute(stmt_top)).all()
    top_selling_items = [
        TopSellingItem(name=row.name, count=int(row.total_qty)) for row in top_rows
    ]

    return DashboardStatsResponse(
        new_orders_7d=new_orders_7d,
        total_revenue_7d=total_revenue_7d,
        average_order_value=avg_order_value,
        unread_messages=unread_messages,
        new_reviews_7d=new_reviews_7d,
        new_bookmarks_7d=new_bookmarks_7d,
        order_volume_14d=order_volume_14d,
        daily_revenue_30d=daily_revenue_30d,
        total_revenue_30d=total_revenue_30d,
        total_orders_30d=total_orders_30d,
        top_selling_items=top_selling_items,
    )
