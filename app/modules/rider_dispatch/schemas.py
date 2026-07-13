from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RiderDispatchCandidateResponse(BaseModel):
    id: int
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    assignment_type: str = "open"
    rider_work_mode: str = "freelance"
    is_accepting_offers: bool = False
    busy: bool = False
    distance_km: float | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None


class RiderInvitationCreateRequest(BaseModel):
    invited_email: str = Field(min_length=3, max_length=255)
    invitation_type: str = Field(default="private", pattern="^(private|preferred)$")
    notes: str | None = Field(default=None, max_length=1000)


class RiderInvitationActionRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class RiderInvitationResponse(BaseModel):
    id: int
    restaurant_id: int
    inviter_user_id: int
    invited_user_id: int | None = None
    invited_email: str
    invitation_type: str
    status: str
    notes: str | None = None
    responded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RiderDispatchOfferResponse(BaseModel):
    id: int
    order_id: int
    restaurant_id: int
    rider_user_id: int
    tier: str
    status: str
    round_number: int
    rank_index: int
    expires_at: datetime | None = None
    responded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
