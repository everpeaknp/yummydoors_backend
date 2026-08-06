from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.payments.schemas import EsewaVerifyRequest, PaymentResponse
from app.modules.payments.service import PaymentService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/esewa/verify", response_model=ApiResponse[PaymentResponse])
async def verify_esewa_payment(
    payload: EsewaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Independently verify an eSewa transaction with eSewa's own API.

    The client (mobile app) only ever sends us the transaction reference it
    got back from the eSewa SDK — never the merchant secret. This endpoint is
    the only place that secret is used, and it's read from server config.
    """
    service = PaymentService(db)
    payment = await service.verify_esewa_payment(customer_id=current_user.id, payload=payload)
    return ApiResponse(message="Payment verified.", data=payment)
