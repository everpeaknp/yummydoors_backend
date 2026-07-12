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


class UserSnapshot(BaseModel):
    id: int
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    restaurantId: int
    restaurantName: str
    restaurantSlug: str
    restaurantLatitude: float | None = None
    restaurantLongitude: float | None = None
    restaurantTags: str
    restaurantLogo: str
    deliveryTime: str
    status: OrderStatus
    items: list[OrderItemResponse]
    totalPrice: float
    orderNumber: str
    paymentMethod: str | None = None
    address: OrderAddressSnapshot | None = None
    rider: UserSnapshot | None = None
    needsCutlery: bool = True
    cookingRequest: str | None = None
    deliveryInstruction: str | None = None
    confirmedAt: datetime | None = None
    preparingAt: datetime | None = None
    riderAssignedAt: datetime | None = None
    pickedUpAt: datetime | None = None
    deliveredAt: datetime | None = None
    cancelledAt: datetime | None = None
    riderAssignmentState: str = "unassigned"
    riderAssignmentTier: str | None = None
    riderOfferExpiresAt: datetime | None = None
    pricing: OrderPricingBreakdown = Field(default_factory=OrderPricingBreakdown)
    timeline: list[OrderTimelineEvent] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MerchantOrderResponse(BaseModel):
    id: int
    customerId: int
    restaurantId: int
    orderNumber: str
    restaurantName: str
    restaurantSlug: str | None = None
    restaurantLatitude: float | None = None
    restaurantLongitude: float | None = None
    customerName: str
    date: str
    status: OrderStatus
    totalPrice: float
    items: list[OrderItemResponse]
    deliveryTime: str | None = None
    address: OrderAddressSnapshot | None = None
    rider: UserSnapshot | None = None
    confirmedAt: datetime | None = None
    preparingAt: datetime | None = None
    riderAssignedAt: datetime | None = None
    pickedUpAt: datetime | None = None
    deliveredAt: datetime | None = None
    cancelledAt: datetime | None = None
    riderAssignmentState: str = "unassigned"
    riderAssignmentTier: str | None = None
    riderOfferExpiresAt: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RiderAssignmentRequest(BaseModel):
    rider_user_id: int


class RiderSummaryResponse(BaseModel):
    id: int
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    assignment_type: str = "open"
    rider_work_mode: str = "freelance"
    busy: bool = False
    distance_km: float | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None
    restaurant_ids: list[int] = Field(default_factory=list)

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
