from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.models import FoodType
from app.modules.merchandising.models import PromoPlacement, PromoTargetType


class AdminOperatorResponse(BaseModel):
    id: int
    email: str | None
    phone: str | None
    full_name: str
    status: str
    roles: list[str]
    restaurant_ids: list[int]
    workspace_ids: list[int]


class AdminUserStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|suspended)$")


class AdminWorkspaceStatusResponse(BaseModel):
    id: int
    name: str
    workspace_type: str
    status: str
    primary_restaurant_id: int | None

    model_config = ConfigDict(from_attributes=True)


class AdminWorkspaceStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|suspended)$")


class AdminCategoryBase(BaseModel):
    slug: str = Field(..., max_length=100)
    name: str = Field(..., max_length=100)
    icon_url: str | None = Field(default=None, max_length=500)
    sort_order: int = 0
    is_featured: bool = True
    is_active: bool = True


class AdminCategoryCreate(AdminCategoryBase):
    slug: str | None = Field(default=None, max_length=100)


class AdminCategoryUpdate(BaseModel):
    slug: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=100)
    icon_url: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None
    is_featured: bool | None = None
    is_active: bool | None = None


class AdminCategoryResponse(AdminCategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AdminRestaurantBase(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    integration_mode: str = Field(default="external", max_length=32)
    status: str = Field(default="draft", max_length=32)
    cover_image_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    short_description: str | None = Field(default=None, max_length=500)
    primary_cuisine_label: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=100)
    latitude: float | None = None
    longitude: float | None = None
    rating_average: float = 0.0
    review_count: int = 0
    supports_delivery: bool = True
    has_free_delivery: bool = False
    offer_text: str | None = Field(default=None, max_length=255)
    delivery_eta_min_minutes: int | None = None
    delivery_eta_max_minutes: int | None = None
    rider_dispatch_policy: str = "ranked"
    rider_private_offer_timeout_seconds: int = 60
    rider_preferred_offer_timeout_seconds: int = 180
    rider_open_offer_timeout_seconds: int = 300
    sort_rank: int = 0
    is_featured: bool = False
    category_ids: list[int] = []


class AdminRestaurantCreate(AdminRestaurantBase):
    pass


class AdminRestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    integration_mode: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    cover_image_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    short_description: str | None = Field(default=None, max_length=500)
    primary_cuisine_label: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=100)
    latitude: float | None = None
    longitude: float | None = None
    rating_average: float | None = None
    review_count: int | None = None
    supports_delivery: bool | None = None
    has_free_delivery: bool | None = None
    offer_text: str | None = Field(default=None, max_length=255)
    delivery_eta_min_minutes: int | None = None
    delivery_eta_max_minutes: int | None = None
    rider_dispatch_policy: str | None = None
    rider_private_offer_timeout_seconds: int | None = None
    rider_preferred_offer_timeout_seconds: int | None = None
    rider_open_offer_timeout_seconds: int | None = None
    sort_rank: int | None = None
    is_featured: bool | None = None
    category_ids: list[int] | None = None


class AdminRestaurantResponse(BaseModel):
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
    offer_text: str | None = None
    delivery_eta_min_minutes: int | None = None
    delivery_eta_max_minutes: int | None = None
    rider_dispatch_policy: str = "ranked"
    rider_private_offer_timeout_seconds: int = 60
    rider_preferred_offer_timeout_seconds: int = 180
    rider_open_offer_timeout_seconds: int = 300
    sort_rank: int
    is_featured: bool
    categories: list[AdminCategoryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AdminMenuItemBase(BaseModel):
    restaurant_id: int
    category_id: int | None = None
    slug: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=500)
    price: float
    currency_code: str = "NPR"
    is_available: bool = True
    food_type: FoodType | None = None
    is_spicy: bool = False
    is_featured: bool = False
    is_popular: bool = False
    popularity_score: int = 0
    rating_average: float = 0.0
    rating_count: int = 0


class AdminMenuItemCreate(AdminMenuItemBase):
    slug: str | None = Field(default=None, max_length=255)


class AdminMenuItemUpdate(BaseModel):
    restaurant_id: int | None = None
    category_id: int | None = None
    slug: str | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=500)
    price: float | None = None
    currency_code: str | None = Field(default=None, max_length=10)
    is_available: bool | None = None
    food_type: FoodType | None = None
    is_spicy: bool | None = None
    is_featured: bool | None = None
    is_popular: bool | None = None
    popularity_score: int | None = None
    rating_average: float | None = None
    rating_count: int | None = None


class AdminMenuItemResponse(AdminMenuItemBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AdminModifierGroupCreate(BaseModel):
    menu_item_id: int
    name: str = Field(..., min_length=1, max_length=255)
    is_required: bool = False
    min_selections: int = Field(default=0, ge=0)
    max_selections: int = Field(default=1, ge=1)


class AdminModifierItemCreate(BaseModel):
    group_id: int
    name: str = Field(..., min_length=1, max_length=255)
    price_adjustment: float = Field(default=0.0, ge=0)
    is_available: bool = True


class AdminAddOnCreate(BaseModel):
    menu_item_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(default=0.0, ge=0)
    currency_code: str = Field(default="NPR", min_length=3, max_length=10)
    is_available: bool = True
    max_quantity: int = Field(default=1, ge=1, le=99)


class AdminPromoBase(BaseModel):
    title: str = Field(..., max_length=255)
    subtitle: str | None = Field(default=None, max_length=255)
    image_url: str = Field(..., max_length=500)
    image_url_mobile: str | None = Field(default=None, max_length=500)
    placement: PromoPlacement
    target_type: PromoTargetType
    target_id: int | None = None
    target_url: str | None = Field(default=None, max_length=500)
    cta_text: str | None = Field(default=None, max_length=100)
    sort_order: int = 0
    is_active: bool = True
    start_at: datetime | None = None
    end_at: datetime | None = None


class AdminPromoCreate(AdminPromoBase):
    pass


class AdminPromoUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    subtitle: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=500)
    image_url_mobile: str | None = Field(default=None, max_length=500)
    placement: PromoPlacement | None = None
    target_type: PromoTargetType | None = None
    target_id: int | None = None
    target_url: str | None = Field(default=None, max_length=500)
    cta_text: str | None = Field(default=None, max_length=100)
    sort_order: int | None = None
    is_active: bool | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class AdminPromoResponse(AdminPromoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AdminFeaturedVideoCreate(BaseModel):
    title: str = Field(..., max_length=255)
    subtitle: str | None = Field(default=None, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    video_url: str = Field(..., max_length=500)
    is_active: bool = True
    sort_order: int = 0


class AdminFeaturedVideoUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    subtitle: str | None = Field(default=None, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    video_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    sort_order: int | None = None


class AdminFeaturedVideoResponse(BaseModel):
    id: int
    title: str
    subtitle: str | None = None
    thumbnail_url: str | None = None
    video_url: str
    is_active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)
