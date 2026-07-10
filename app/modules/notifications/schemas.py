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
