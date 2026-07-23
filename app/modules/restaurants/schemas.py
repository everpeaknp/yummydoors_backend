from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.catalog.schemas import MenuItemSummary
from app.modules.merchandising.schemas import FeaturedVideoResponse, PromoBannerResponse


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
    icon_url: str | None = None
    sort_order: int = 0
    is_featured: bool = False


class MerchantCategoryUpdate(BaseModel):
    name: str | None = None
    icon_url: str | None = None
    sort_order: int | None = None
    is_featured: bool | None = None


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
    latitude: float | None = None
    longitude: float | None = None
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


class GalleryImageResponse(BaseModel):
    id: int
    image_url: str
    caption: str | None = None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class GalleryImageCreate(BaseModel):
    image_url: str
    caption: str | None = None
    sort_order: int = 0


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
    image_urls: list[str] = []


class RestaurantReviewCreate(BaseModel):
    rating: float
    comment: str | None = None
    order_id: int | None = None
    image_urls: list[str] = []

    @field_validator("image_urls")
    @classmethod
    def limit_images(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            raise ValueError("You can upload at most 5 images per review.")
        return v


class RestaurantReviewUpdate(BaseModel):
    rating: float | None = None
    comment: str | None = None
    image_urls: list[str] | None = None

    @field_validator("image_urls")
    @classmethod
    def limit_images(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) > 5:
            raise ValueError("You can upload at most 5 images per review.")
        return v


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
    gallery_images: list[GalleryImageResponse] = []


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
    rider_dispatch_policy: str = "ranked"
    rider_private_offer_timeout_seconds: int = 60
    rider_preferred_offer_timeout_seconds: int = 180
    rider_open_offer_timeout_seconds: int = 300
    sort_rank: int
    is_featured: bool
    categories: list[CategorySummary] = []
    gallery_images: list[GalleryImageResponse] = []


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
    rider_dispatch_policy: str | None = None
    rider_private_offer_timeout_seconds: int | None = None
    rider_preferred_offer_timeout_seconds: int | None = None
    rider_open_offer_timeout_seconds: int | None = None
    category_ids: list[int] | None = None


class HomeLocationContext(BaseModel):
    location_title: str
    location_subtitle: str
    selected_address_id: int | None = None
    saved_addresses_count: int = 0
    selected_address_label: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class HomeFeedFilterOption(BaseModel):
    key: str
    label: str
    type: str = "quick_filter"
    query_param: str | None = None
    value: str | bool | None = None
    is_active: bool = True


class HomeFeedResponse(BaseModel):
    location_context: HomeLocationContext
    categories: list[CategorySummary]
    restaurants: list[RestaurantCardSummary]
    explore_restaurants: list[RestaurantCardSummary] = []
    filters: list[HomeFeedFilterOption] = []
    promos: list[PromoBannerResponse] = []
    hero_promos: list[PromoBannerResponse] = []
    banner_promos: list[PromoBannerResponse] = []
    recommended_items: list[MenuItemSummary] = []
    popular_foods: list[MenuItemSummary] = []
    featured_videos: list[FeaturedVideoResponse] = []


class DashboardStatPoint(BaseModel):
    date: str   # YYYY-MM-DD
    count: int
    revenue: float = 0.0


class TopSellingItem(BaseModel):
    name: str
    count: int


class DashboardStatsResponse(BaseModel):
    # Hero-card numbers
    new_orders_7d: int = 0
    total_revenue_7d: float = 0.0
    average_order_value: float = 0.0
    unread_messages: int = 0
    new_reviews_7d: int = 0
    new_bookmarks_7d: int = 0

    # Chart data
    order_volume_14d: list[DashboardStatPoint] = []
    daily_revenue_30d: list[DashboardStatPoint] = []

    # Deep-dive analytics
    total_revenue_30d: float = 0.0
    total_orders_30d: int = 0
    top_selling_items: list[TopSellingItem] = []
