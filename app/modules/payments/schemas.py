from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.payments.models import PaymentStatus


class EsewaVerifyRequest(BaseModel):
    order_id: int
    ref_id: str | None = None
    product_id: str | None = None
    amount: float | None = None


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    method: str
    provider: str | None = None
    provider_ref: str | None = None
    amount: float
    currency_code: str
    status: PaymentStatus
    failure_reason: str | None = None
    initiated_at: datetime
    confirmed_at: datetime | None = None
    failed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
