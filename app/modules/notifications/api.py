from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.notifications.schemas import (
    WebPushPublicKeyResponse,
    WebPushSubscriptionCreate,
    WebPushSubscriptionDelete,
    WebPushSubscriptionResponse,
)
from app.modules.notifications.service import NotificationService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/notifications/webpush", tags=["Notifications"])


@router.get("/public-key", response_model=ApiResponse[WebPushPublicKeyResponse])
async def get_web_push_public_key(db: AsyncSession = Depends(get_db)):
    service = NotificationService(db)
    return ApiResponse(
        message="Web push public key fetched successfully.",
        data=WebPushPublicKeyResponse(public_key=service.get_public_vapid_key()),
    )


@router.post("/subscribe", response_model=ApiResponse[WebPushSubscriptionResponse])
async def subscribe_web_push(
    payload: WebPushSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(default=None),
):
    service = NotificationService(db)
    record = await service.register_web_push_subscription(
        user_id=current_user.id,
        payload=payload,
        user_agent=user_agent,
    )
    return ApiResponse(
        message="Web push subscription saved successfully.",
        data=WebPushSubscriptionResponse.model_validate(record),
    )


@router.delete("/unsubscribe", status_code=204)
async def unsubscribe_web_push(
    payload: WebPushSubscriptionDelete,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    await service.unregister_web_push_subscription(payload.endpoint)
    return Response(status_code=204)
