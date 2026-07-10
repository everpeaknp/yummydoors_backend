from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.notifications.schemas import (
    FcmTokenCreate,
    FcmTokenResponse,
    FcmTokenStatusResponse,
    WebPushPublicKeyResponse,
    WebPushStatusResponse,
    WebPushSubscriptionCreate,
    WebPushSubscriptionDelete,
    WebPushSubscriptionResponse,
)
from app.modules.notifications.service import NotificationService
from app.schemas.common import ApiResponse

router = APIRouter()
webpush_router = APIRouter(prefix="/notifications/webpush", tags=["Notifications"])
fcm_router = APIRouter(prefix="/notifications/fcm", tags=["Notifications"])


@webpush_router.get("/public-key", response_model=ApiResponse[WebPushPublicKeyResponse])
async def get_web_push_public_key(db: AsyncSession = Depends(get_db)):
    service = NotificationService(db)
    return ApiResponse(
        message="Web push public key fetched successfully.",
        data=WebPushPublicKeyResponse(public_key=service.get_public_vapid_key()),
    )


@webpush_router.get("/status", response_model=ApiResponse[WebPushStatusResponse])
async def get_web_push_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    status_payload = await service.get_web_push_status(current_user.id)
    return ApiResponse(
        message="Web push status fetched successfully.",
        data=WebPushStatusResponse.model_validate(status_payload),
    )


@webpush_router.post("/subscribe", response_model=ApiResponse[WebPushSubscriptionResponse])
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


@webpush_router.delete("/unsubscribe", status_code=204)
async def unsubscribe_web_push(
    payload: WebPushSubscriptionDelete,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    await service.unregister_web_push_subscription(payload.endpoint)
    return Response(status_code=204)


@fcm_router.get("/status", response_model=ApiResponse[FcmTokenStatusResponse])
async def get_fcm_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    status_payload = await service.get_fcm_status(current_user.id)
    return ApiResponse(
        message="FCM status fetched successfully.",
        data=FcmTokenStatusResponse.model_validate(status_payload),
    )


@fcm_router.post("/register", response_model=ApiResponse[FcmTokenResponse])
async def register_fcm_token(
    payload: FcmTokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(default=None),
):
    service = NotificationService(db)
    record = await service.register_fcm_token(
        user_id=current_user.id,
        payload=payload,
        user_agent=user_agent,
    )
    return ApiResponse(
        message="FCM token saved successfully.",
        data=FcmTokenResponse.model_validate(record),
    )


router.include_router(webpush_router)
router.include_router(fcm_router)
