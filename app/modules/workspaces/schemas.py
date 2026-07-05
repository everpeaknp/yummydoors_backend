from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class WorkspaceSummary(BaseModel):
    id: int
    workspace_type: str
    name: str
    slug: str | None
    status: str
    membership_role: str
    is_primary: bool
    primary_restaurant_id: int | None = None
    primary_restaurant_name: str | None = None


class WorkspaceListResponse(BaseModel):
    active_workspace_id: int | None
    active_workspace: WorkspaceSummary | None
    available_workspaces: list[WorkspaceSummary]


class WorkspaceSwitchRequest(BaseModel):
    workspace_id: int


class MerchantRestaurantSummary(BaseModel):
    id: int
    name: str
    slug: str
    city: str | None = None
    area: str | None = None
    integration_mode: str
    status: str
    logo_url: str | None = None
    cover_image_url: str | None = None
    primary_cuisine_label: str | None = None
    is_active_context: bool
    ownership_types: list[str] = []


class MerchantRestaurantListResponse(BaseModel):
    active_restaurant_id: int | None
    items: list[MerchantRestaurantSummary]


class MerchantRestaurantSwitchRequest(BaseModel):
    restaurant_id: int


class MerchantApplicationCreateRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=255)
    contact_name: str = Field(min_length=2, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_contact_method(self) -> "MerchantApplicationCreateRequest":
        if not self.contact_email and not self.contact_phone:
            raise ValueError("Either contact email or contact phone is required.")
        return self


class MerchantRestaurantRequestCreate(BaseModel):
    request_type: str = Field(default="create_external", pattern="^(create_external|claim_existing|pos_link)$")
    restaurant_id: int | None = None
    requested_name: str = Field(min_length=2, max_length=255)
    requested_slug: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=100)
    latitude: float | None = None
    longitude: float | None = None
    pos_restaurant_id: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)


class MerchantApplicationUpdateRequest(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=255)
    contact_name: str | None = Field(default=None, min_length=2, max_length=255)
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    notes: str | None = Field(default=None, max_length=1000)


class MerchantApplicationReviewRequest(BaseModel):
    admin_notes: str | None = Field(default=None, max_length=1000)


class MerchantRestaurantRequestResponse(BaseModel):
    id: int
    request_type: str
    status: str
    restaurant_id: int | None
    requested_name: str
    requested_slug: str | None
    city: str | None
    area: str | None
    latitude: float | None
    longitude: float | None
    source_system: str
    pos_restaurant_id: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MerchantApplicationResponse(BaseModel):
    id: int
    user_id: int
    workspace_id: int | None
    workspace: WorkspaceSummary | None
    status: str
    business_name: str
    contact_name: str
    contact_email: str | None
    contact_phone: str | None
    notes: str | None
    admin_notes: str | None
    restaurant_requests: list[MerchantRestaurantRequestResponse]
    created_at: datetime
    updated_at: datetime
