from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.notifications.schemas import (
    FcmTokenCreate,
    FcmTokenResponse,
    FcmTokenStatusResponse,
    NotificationCountResponse,
    UserNotificationResponse,
    WebPushPublicKeyResponse,
    WebPushStatusResponse,
    WebPushSubscriptionCreate,
    WebPushSubscriptionDelete,
    WebPushSubscriptionResponse,
)
from app.modules.notifications.service import NotificationService
from app.modules.workspaces.repository import WorkspaceRepository
from app.schemas.common import ApiResponse

router = APIRouter()
webpush_router = APIRouter(prefix="/notifications/webpush", tags=["Notifications"])
fcm_router = APIRouter(prefix="/notifications/fcm", tags=["Notifications"])


def _to_notification_response(record) -> UserNotificationResponse:
    return UserNotificationResponse(
        id=record.id,
        recipient_user_id=record.recipient_user_id,
        audience=record.audience,
        category=record.category,
        event_key=record.event_key,
        title=record.title,
        body=record.body,
        deep_link=record.deep_link,
        payload_json=record.payload_json,
        restaurant_id=record.restaurant_id,
        order_id=record.order_id,
        message_id=record.message_id,
        actor_user_id=record.actor_user_id,
        read_at=record.read_at,
        dismissed_at=record.dismissed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        is_read=record.read_at is not None,
        is_dismissed=record.dismissed_at is not None,
    )


async def _resolve_merchant_restaurant_id(
    *,
    current_user: User,
    db: AsyncSession,
    audience: str | None,
    restaurant_id: int | None,
) -> int | None:
    if audience != "merchant":
        return restaurant_id
    if restaurant_id is not None:
        return restaurant_id

    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_active_workspace(current_user.id)
    if workspace is None or workspace.workspace_type != "merchant" or workspace.primary_restaurant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active merchant workspace.",
        )
    return workspace.primary_restaurant_id


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


@router.get("/me", response_model=ApiResponse[list[UserNotificationResponse]])
async def list_my_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audience: str | None = None,
    restaurant_id: int | None = None,
    unread_only: bool = False,
    include_dismissed: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    service = NotificationService(db)
    resolved_restaurant_id = await _resolve_merchant_restaurant_id(
        current_user=current_user,
        db=db,
        audience=audience,
        restaurant_id=restaurant_id,
    )
    records = await service.list_notifications(
        recipient_user_id=current_user.id,
        audience=audience,
        restaurant_id=resolved_restaurant_id,
        unread_only=unread_only,
        include_dismissed=include_dismissed,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(
        message="Notifications fetched successfully.",
        data=[_to_notification_response(record) for record in records],
    )


@router.get("/me/unread-count", response_model=ApiResponse[NotificationCountResponse])
async def get_my_notification_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audience: str | None = None,
    restaurant_id: int | None = None,
):
    service = NotificationService(db)
    resolved_restaurant_id = await _resolve_merchant_restaurant_id(
        current_user=current_user,
        db=db,
        audience=audience,
        restaurant_id=restaurant_id,
    )
    unread_count = await service.count_notifications(
        recipient_user_id=current_user.id,
        audience=audience,
        restaurant_id=resolved_restaurant_id,
        unread_only=True,
    )
    total_count = await service.count_notifications(
        recipient_user_id=current_user.id,
        audience=audience,
        restaurant_id=resolved_restaurant_id,
    )
    return ApiResponse(
        message="Notification counts fetched successfully.",
        data=NotificationCountResponse(unread_count=unread_count, total_count=total_count),
    )


@router.patch("/me/read-all", response_model=ApiResponse[dict])
async def mark_my_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audience: str | None = None,
    restaurant_id: int | None = None,
):
    service = NotificationService(db)
    resolved_restaurant_id = await _resolve_merchant_restaurant_id(
        current_user=current_user,
        db=db,
        audience=audience,
        restaurant_id=restaurant_id,
    )
    updated_count = await service.mark_all_notifications_read(
        recipient_user_id=current_user.id,
        audience=audience,
        restaurant_id=resolved_restaurant_id,
    )
    return ApiResponse(
        message="Notifications marked as read.",
        data={"updated_count": updated_count},
    )


@router.patch("/me/{notification_id}/read", response_model=ApiResponse[UserNotificationResponse])
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    record = await service.mark_notification_read(
        recipient_user_id=current_user.id,
        notification_id=notification_id,
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return ApiResponse(
        message="Notification marked as read.",
        data=_to_notification_response(record),
    )


@router.delete("/me/{notification_id}", status_code=204)
async def dismiss_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    await service.dismiss_notification(
        recipient_user_id=current_user.id,
        notification_id=notification_id,
    )
    return Response(status_code=204)


router.include_router(webpush_router)
router.include_router(fcm_router)
