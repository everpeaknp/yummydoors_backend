from __future__ import annotations

from pydantic import BaseModel
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.merchandising.schemas import PromoBannerResponse


class CategorySummary(BaseModel):
    id: int
    slug: str
    name: str
    icon_url: str | None = None
    sort_order: int
    is_featured: bool


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
    offer_text: str | None = None
    delivery_eta_min_minutes: int | None = None
    delivery_eta_max_minutes: int | None = None
    is_featured: bool
    categories: list[CategorySummary] = []


class RestaurantListResponse(BaseModel):
    items: list[RestaurantCardSummary]
    total: int


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
    recommended_items: list[MenuItemSummary] = []
    popular_foods: list[MenuItemSummary] = []
