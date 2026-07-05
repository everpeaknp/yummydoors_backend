from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RestaurantTableSummary(BaseModel):
    id: int
    code: str
    label: str
    zone: str | None = None
    min_guest_count: int
    max_guest_count: int

    model_config = ConfigDict(from_attributes=True)


class ReservationAvailabilitySlot(BaseModel):
    time: str
    is_available: bool
    remaining_tables: int
    available_table_ids: list[int] = []


class ReservationAvailabilityResponse(BaseModel):
    restaurant_id: int
    restaurant_slug: str
    reservation_date: date
    guest_count: int | None = None
    available_tables: list[RestaurantTableSummary] = []
    slots: list[ReservationAvailabilitySlot] = []


class ReservationCreateRequest(BaseModel):
    reservation_date: date
    reservation_time: str = Field(..., min_length=4, max_length=10)
    guest_count: int = Field(..., ge=1, le=50)
    contact_name: str = Field(..., min_length=2, max_length=255)
    contact_phone: str = Field(..., min_length=5, max_length=32)
    contact_email: EmailStr | None = None
    special_request: str | None = Field(default=None, max_length=1000)
    table_id: int | None = None


class ReservationCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ReservationStatusEventResponse(BaseModel):
    status: str
    note: str | None = None
    created_at: str


class ReservationResponse(BaseModel):
    id: int
    reservation_code: str
    status: str
    restaurant_id: int
    restaurant_name: str
    restaurant_slug: str
    restaurant_logo_url: str | None = None
    reservation_date: date
    reservation_time: str
    guest_count: int
    contact_name: str
    contact_phone: str
    contact_email: EmailStr | None = None
    special_request: str | None = None
    selected_table: RestaurantTableSummary | None = None
    created_at: str
    updated_at: str
    status_events: list[ReservationStatusEventResponse] = []

