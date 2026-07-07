from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.orders.models import OrderStatus


class OrderItemResponse(BaseModel):
    name: str
    price: float
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class OrderAddressSnapshot(BaseModel):
    id: int | None = None
    recipient_name: str | None = None
    phone_number: str | None = None
    address_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class OrderPricingBreakdown(BaseModel):
    items_total: float = 0.0
    coupon_discount: float = 0.0
    delivery_fee: float = 0.0
    service_fee: float = 0.0
    tax_amount: float = 0.0
    subtotal_amount: float = 0.0
    total_amount: float = 0.0


class OrderTimelineEvent(BaseModel):
    key: str
    label: str
    state: str
    timestamp: datetime | None = None
    description: str | None = None


class OrderResponse(BaseModel):
    restaurantName: str
    restaurantTags: str
    restaurantLogo: str
    deliveryTime: str
    status: OrderStatus
    items: list[OrderItemResponse]
    totalPrice: float
    orderNumber: str
    paymentMethod: str | None = None
    address: OrderAddressSnapshot | None = None
    needsCutlery: bool = True
    cookingRequest: str | None = None
    deliveryInstruction: str | None = None
    pricing: OrderPricingBreakdown = Field(default_factory=OrderPricingBreakdown)
    timeline: list[OrderTimelineEvent] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CheckoutRequest(BaseModel):
    payment_method: str = "cash"
    address_id: int | None = None
    coupon_code: str | None = Field(default=None, max_length=64)
    needs_cutlery: bool | None = None
    cooking_request: str | None = Field(default=None, max_length=1000)
    delivery_instruction: str | None = Field(default=None, max_length=1000)

class OrderSummaryItemRequest(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, default=1)
    modifier_ids: list[int] = Field(default_factory=list)

class OrderSummaryRequest(BaseModel):
    restaurant_id: int
    items: list[OrderSummaryItemRequest]
    coupon_code: str | None = None

class OrderSummaryResponse(BaseModel):
    items: list[OrderItemResponse]
    pricing: OrderPricingBreakdown
