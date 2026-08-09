from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RiderWalletResponse(BaseModel):
    riderUserId: int
    riderName: str | None = None
    balance: float
    canAcceptOffers: bool

    model_config = ConfigDict(from_attributes=True)


class RiderWalletTransactionResponse(BaseModel):
    id: int
    kind: str
    amount: float
    balanceAfter: float
    note: str | None = None
    orderId: int | None = None
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminWalletTopUpRequest(BaseModel):
    amount: float = Field(gt=0)
    note: str | None = None
