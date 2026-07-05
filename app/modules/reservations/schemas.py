from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.reservations.models import ReservationStatus


class RestaurantTableSummary(BaseModel):
    id: int
    code: str
    label: str
    zone: str | None = None
    min_guest_count: int
    max_guest_count: int
    seat_capacity: int
    category: str
    status: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ReservationAvailabilitySlot(BaseModel):
    time: str
    is_available: bool
    remaining_tables: int
    available_table_ids: list[int] = Field(default_factory=list)


class ReservationTableAvailability(BaseModel):
    table: RestaurantTableSummary
    status: str


class ReservationAvailabilityResponse(BaseModel):
    restaurant_id: int
    restaurant_slug: str
    reservation_date: date
    reservation_time: str | None = None
    guest_count: int | None = None
    available_tables: list[RestaurantTableSummary] = Field(default_factory=list)
    slots: list[ReservationAvailabilitySlot] = Field(default_factory=list)
    table_inventory: list[ReservationTableAvailability] = Field(default_factory=list)


class ReservationCreateRequest(BaseModel):
    reservation_date: date
    reservation_time: str = Field(..., min_length=4, max_length=10)
    guest_count: int = Field(..., ge=1, le=50)
    contact_name: str = Field(..., min_length=2, max_length=255)
    contact_phone: str = Field(..., min_length=5, max_length=32)
    contact_email: EmailStr | None = None
    occasion: str | None = Field(default=None, max_length=255)
    special_request: str | None = Field(default=None, max_length=1000)
    table_id: int | None = None


class ReservationCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ReservationStatusUpdateRequest(BaseModel):
    status: ReservationStatus
    note: str | None = Field(default=None, max_length=1000)
    table_id: int | None = None


class RestaurantTableCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=100)
    zone: str | None = Field(default=None, max_length=100)
    min_guest_count: int = Field(default=1, ge=1, le=50)
    max_guest_count: int = Field(default=4, ge=1, le=50)
    status: str = Field(default="active", max_length=32)
    sort_order: int = Field(default=0, ge=0)


class RestaurantTableUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    label: str | None = Field(default=None, min_length=1, max_length=100)
    zone: str | None = Field(default=None, max_length=100)
    min_guest_count: int | None = Field(default=None, ge=1, le=50)
    max_guest_count: int | None = Field(default=None, ge=1, le=50)
    status: str | None = Field(default=None, max_length=32)
    sort_order: int | None = Field(default=None, ge=0)


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
    occasion: str | None = None
    special_request: str | None = None
    cancellation_reason: str | None = None
    source: str
    selected_table: RestaurantTableSummary | None = None
    selected_table_label: str | None = None
    selected_table_zone: str | None = None
    created_at: str
    updated_at: str
    status_events: list[ReservationStatusEventResponse] = Field(default_factory=list)
