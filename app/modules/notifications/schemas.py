from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class WebPushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class WebPushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: WebPushSubscriptionKeys


class WebPushSubscriptionDelete(BaseModel):
    endpoint: str


class WebPushPublicKeyResponse(BaseModel):
    public_key: str


class WebPushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class WebPushStatusResponse(BaseModel):
    has_subscription: bool
    active_subscription_count: int


class FcmTokenCreate(BaseModel):
    token: str
    platform: str = "flutter"


class FcmTokenResponse(BaseModel):
    id: int
    token: str
    platform: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class FcmTokenStatusResponse(BaseModel):
    has_token: bool
    active_token_count: int


class UserNotificationResponse(BaseModel):
    id: int
    recipient_user_id: int
    audience: str
    category: str
    event_key: str
    title: str
    body: str
    deep_link: str | None = None
    payload_json: dict[str, Any] | None = None
    restaurant_id: int | None = None
    order_id: int | None = None
    message_id: int | None = None
    actor_user_id: int | None = None
    read_at: datetime | None = None
    dismissed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    is_read: bool = False
    is_dismissed: bool = False

    model_config = ConfigDict(from_attributes=True)


class NotificationCountResponse(BaseModel):
    unread_count: int
    total_count: int
