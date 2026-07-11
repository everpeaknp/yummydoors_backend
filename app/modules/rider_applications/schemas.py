from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class RiderApplicationCreateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    city_area: str = Field(min_length=2, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    vehicle_type: str = Field(min_length=2, max_length=100)
    availability: str = Field(min_length=2, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_contact_method(self) -> "RiderApplicationCreateRequest":
        if not self.email and not self.phone:
            raise ValueError("Either email or phone is required.")
        return self


class RiderApplicationReviewRequest(BaseModel):
    admin_notes: str | None = Field(default=None, max_length=2000)


class RiderApplicationResponse(BaseModel):
    id: int
    user_id: int
    status: str
    full_name: str
    email: str | None
    phone: str | None
    city_area: str
    address: str | None
    vehicle_type: str
    availability: str
    notes: str | None
    admin_notes: str | None
    reviewed_by_user_id: int | None
    reviewed_by_user_name: str | None = None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
