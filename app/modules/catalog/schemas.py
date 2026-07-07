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

    model_config = ConfigDict(from_attributes=True)

class MenuItemSummary(MenuItemBase):
    id: int
    restaurant_id: int
    category_id: Optional[int] = None
    modifier_groups: List[MenuModifierGroupResponse] = []

    model_config = ConfigDict(from_attributes=True)
