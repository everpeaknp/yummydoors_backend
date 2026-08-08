from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RestaurantSettlementResponse(BaseModel):
    id: int
    orderId: int
    orderNumber: str | None = None
    restaurantId: int
    restaurantName: str | None = None
    paymentMethod: str
    direction: str
    subtotalAmount: float
    commissionRatePercent: float
    commissionAmount: float
    status: str
    settledAt: datetime | None = None
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)
