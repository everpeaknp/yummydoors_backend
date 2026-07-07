from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.merchandising.schemas import PromoBannerResponse


class CategorySummary(BaseModel):
    id: int
    slug: str
    name: str
    icon_url: str | None = None
    sort_order: int
    is_featured: bool

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str
    slug: str
    icon_url: str | None = None
    sort_order: int = 0
    is_featured: bool = False


class CategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    icon_url: str | None = None
    sort_order: int | None = None
    is_featured: bool | None = None


class MerchantCategoryCreate(BaseModel):
    name: str


class MerchantCategoryUpdate(BaseModel):
    name: str | None = None


class RestaurantCardSummary(BaseModel):
    id: int
    slug: str
    name: str
    cover_image_url: str | None = None
    logo_url: str | None = None
    short_description: str | None = None
    primary_cuisine_label: str | None = None
    city: str | None = None
    area: str | None = None
    rating_average: float
    review_count: int
    supports_delivery: bool
    has_free_delivery: bool
    supports_pickup: bool = False
    supports_table_booking: bool = False
    offer_text: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    delivery_eta_min_minutes: int | None = None
    delivery_eta_max_minutes: int | None = None
    opening_time: str | None = None
    closing_time: str | None = None
    is_open_now: bool | None = None
    distance_km: float | None = None
    is_featured: bool
    is_favorited: bool = False
    categories: list[CategorySummary] = []


class RestaurantListResponse(BaseModel):
    items: list[RestaurantCardSummary]
    total: int


class RestaurantMenuSection(BaseModel):
    category_id: int | None = None
    category_slug: str | None = None
    category_name: str
    items: list[MenuItemSummary]


class RestaurantReviewSummary(BaseModel):
    average_rating: float
    total_reviews: int
    highlights: list[str] = []


class RestaurantReviewResponse(BaseModel):
    id: int
    user_id: int | None = None
    author_name: str
    rating: float
    comment: str | None = None
    source: str
    created_at: str
    is_mine: bool = False
    can_edit: bool = False


class RestaurantReviewCreate(BaseModel):
    rating: float
    comment: str | None = None


class RestaurantReviewUpdate(BaseModel):
    rating: float | None = None
    comment: str | None = None


class RestaurantReviewEligibilityResponse(BaseModel):
    can_create_review: bool
    requires_delivered_order: bool = True
    existing_review_id: int | None = None
    reason: str | None = None


class RestaurantDetailResponse(BaseModel):
    restaurant: RestaurantCardSummary
    menu_sections: list[RestaurantMenuSection]
    featured_items: list[MenuItemSummary] = []
    popular_items: list[MenuItemSummary] = []
    related_restaurants: list[RestaurantCardSummary] = []
    about_text: str | None = None
    facilities: list[str] = []
    reviews_summary: RestaurantReviewSummary | None = None
    reviews: list[RestaurantReviewResponse] = []
    viewer_review: RestaurantReviewResponse | None = None
    review_eligibility: RestaurantReviewEligibilityResponse | None = None


class RestaurantSearchMatch(BaseModel):
    restaurant: RestaurantCardSummary
    matched_menu_items: list[MenuItemSummary] = []


class RestaurantSearchResponse(BaseModel):
    items: list[RestaurantSearchMatch]
    total: int


class MerchantRestaurantProfileResponse(BaseModel):
    id: int
    name: str
    slug: str
    integration_mode: str
    status: str
    cover_image_url: str | None = None
    logo_url: str | None = None
    short_description: str | None = None
    primary_cuisine_label: str | None = None
    city: str | None = None
    area: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rating_average: float
    review_count: int
    supports_delivery: bool
    has_free_delivery: bool
    supports_pickup: bool
    supports_table_booking: bool
    offer_text: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    opening_time: str | None = None
    closing_time: str | None = None
    about_text: str | None = None
    facilities_text: str | None = None
    delivery_eta_min_minutes: int | None = None
    delivery_eta_max_minutes: int | None = None
    sort_rank: int
    is_featured: bool
    categories: list[CategorySummary] = []


class MerchantRestaurantProfileUpdate(BaseModel):
    name: str | None = None
    cover_image_url: str | None = None
    logo_url: str | None = None
    short_description: str | None = None
    primary_cuisine_label: str | None = None
    city: str | None = None
    area: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    supports_delivery: bool | None = None
    has_free_delivery: bool | None = None
    supports_pickup: bool | None = None
    supports_table_booking: bool | None = None
    offer_text: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    opening_time: str | None = None
    closing_time: str | None = None
    about_text: str | None = None
    facilities_text: str | None = None
    delivery_eta_min_minutes: int | None = None
    delivery_eta_max_minutes: int | None = None
    category_ids: list[int] | None = None


class HomeLocationContext(BaseModel):
    location_title: str
    location_subtitle: str
    selected_address_id: int | None = None
    saved_addresses_count: int = 0
    selected_address_label: str | None = None


class HomeFeedResponse(BaseModel):
    location_context: HomeLocationContext
    categories: list[CategorySummary]
    restaurants: list[RestaurantCardSummary]
    promos: list[PromoBannerResponse] = []
    hero_promos: list[PromoBannerResponse] = []
    banner_promos: list[PromoBannerResponse] = []
    recommended_items: list[MenuItemSummary] = []
    popular_foods: list[MenuItemSummary] = []
