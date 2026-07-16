from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.modules.catalog.models import FoodType

class MenuModifierItemBase(BaseModel):
    name: str = Field(..., max_length=255)
    price_adjustment: float = 0.0
    is_available: bool = True

class MenuModifierItemResponse(MenuModifierItemBase):
    id: int
    group_id: int
    
    model_config = ConfigDict(from_attributes=True)

class MenuModifierGroupBase(BaseModel):
    name: str = Field(..., max_length=255)
    is_required: bool = False
    min_selections: int = 0
    max_selections: int = 1

class MenuModifierGroupResponse(MenuModifierGroupBase):
    id: int
    menu_item_id: int
    items: List[MenuModifierItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class MenuAddOnBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(default=0.0, ge=0)
    currency_code: str = Field(default="NPR", min_length=3, max_length=10)
    is_available: bool = True
    max_quantity: int = Field(default=1, ge=1, le=99)


class MenuAddOnResponse(MenuAddOnBase):
    id: int
    menu_item_id: int

    model_config = ConfigDict(from_attributes=True)


class MenuModifierGroupCreate(MenuModifierGroupBase):
    pass


class MenuModifierItemCreate(MenuModifierItemBase):
    pass


class MenuModifierGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_required: bool | None = None
    min_selections: int | None = Field(default=None, ge=0)
    max_selections: int | None = Field(default=None, ge=1)


class MenuModifierItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price_adjustment: float | None = Field(default=None, ge=0)
    is_available: bool | None = None


class MenuAddOnUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, ge=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=10)
    is_available: bool | None = None
    max_quantity: int | None = Field(default=None, ge=1, le=99)

class MenuItemCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    price: float
    currency_code: str = "NPR"
    category_id: Optional[int] = None
    food_type: Optional[FoodType] = None
    is_available: bool = True
    is_spicy: bool = False


class MerchantMenuItemCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    price: float
    currency_code: str = "NPR"
    category_id: Optional[int] = None
    food_type: Optional[FoodType] = None
    is_available: bool = True
    is_spicy: bool = False

class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = None
    currency_code: Optional[str] = None
    category_id: Optional[int] = None
    food_type: Optional[FoodType] = None
    is_available: Optional[bool] = None
    is_spicy: Optional[bool] = None


class MerchantMenuItemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = None
    currency_code: Optional[str] = None
    category_id: Optional[int] = None
    food_type: Optional[FoodType] = None
    is_available: Optional[bool] = None
    is_spicy: Optional[bool] = None

class MenuItemBase(BaseModel):
    slug: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    price: float
    currency_code: str = "NPR"
    is_available: bool = True
    food_type: Optional[FoodType] = None
    is_spicy: bool = False
    is_featured: bool = False
    is_popular: bool = False
    popularity_score: int = 0
    rating_average: float = 0.0
    rating_count: int = 0
    is_favorited: bool = False

class MenuItemResponse(MenuItemBase):
    id: int
    restaurant_id: int
    category_id: Optional[int] = None
    modifier_groups: List[MenuModifierGroupResponse] = []
    add_ons: List[MenuAddOnResponse] = []

    model_config = ConfigDict(from_attributes=True)

class MenuItemSummary(MenuItemBase):
    id: int
    restaurant_id: int
    category_id: Optional[int] = None
    modifier_groups: List[MenuModifierGroupResponse] = []
    add_ons: List[MenuAddOnResponse] = []

    model_config = ConfigDict(from_attributes=True)
