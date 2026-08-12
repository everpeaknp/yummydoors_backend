from datetime import datetime

from pydantic import BaseModel, Field


class SetRiderSalaryRequest(BaseModel):
    monthlyAmount: float = Field(ge=0)


class RiderSalaryResponse(BaseModel):
    riderUserId: int
    riderName: str
    monthlyAmount: float
    updatedAt: datetime


class RiderPayrollPaymentResponse(BaseModel):
    id: int
    riderUserId: int
    riderName: str
    period: str
    amount: float
    status: str
    paidAt: datetime | None = None
    createdAt: datetime


class MyPayrollStatusResponse(BaseModel):
    monthlyAmount: float | None = None
    currentPeriod: str
    currentPeriodStatus: str | None = None
    lastPaidAt: datetime | None = None
