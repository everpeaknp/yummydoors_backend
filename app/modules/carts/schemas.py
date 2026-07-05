from pydantic import BaseModel, ConfigDict, Field

from app.modules.carts.models import CartStatus


class CartItemBase(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, default=1)


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemResponse(CartItemBase):
    id: int
    name: str
    price: float
    image_url: str | None

    model_config = ConfigDict(from_attributes=True)


class CartAddressSummary(BaseModel):
    id: int
    label: str | None
    recipient_name: str
    phone_number: str
    address_summary: str
    latitude: float | None
    longitude: float | None


class CartPricingBreakdown(BaseModel):
    items_total: float = 0.0
    coupon_discount: float = 0.0
    delivery_fee: float = 0.0
    service_fee: float = 0.0
    tax_amount: float = 0.0
    subtotal_amount: float = 0.0
    total_amount: float = 0.0


class CartBase(BaseModel):
    restaurant_id: int


class CartCreate(CartBase):
    pass


class CartContextUpdate(BaseModel):
    address_id: int | None = None
    needs_cutlery: bool | None = None
    cooking_request: str | None = Field(default=None, max_length=1000)
    delivery_instruction: str | None = Field(default=None, max_length=1000)


class CartCouponApplyRequest(BaseModel):
    coupon_code: str = Field(min_length=2, max_length=64)


class CartResponse(CartBase):
    id: int
    status: CartStatus
    items: list[CartItemResponse] = []
    items_count: int = 0
    total_price: float = 0.0
    restaurant_name: str
    restaurant_image_asset: str | None
    eta_text: str = "20-30 min"
    address: CartAddressSummary | None = None
    needs_cutlery: bool = True
    cooking_request: str | None = None
    delivery_instruction: str | None = None
    coupon_code: str | None = None
    pricing: CartPricingBreakdown = Field(default_factory=CartPricingBreakdown)

    model_config = ConfigDict(from_attributes=True)
