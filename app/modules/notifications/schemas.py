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
