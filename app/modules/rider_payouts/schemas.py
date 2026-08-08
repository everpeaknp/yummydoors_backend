from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RiderPayoutResponse(BaseModel):
    id: int
    orderId: int
    orderNumber: str | None = None
    riderUserId: int
    riderName: str | None = None
    restaurantId: int
    restaurantName: str | None = None
    distanceKm: float
    baseFare: float
    distanceFare: float
    grossFare: float
    commissionRatePercent: float
    commissionAmount: float
    payoutAmount: float
    status: str
    paidAt: datetime | None = None
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkPayoutPaidRequest(BaseModel):
    note: str | None = None
