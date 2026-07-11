from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerAddressBase(BaseModel):
    label: Optional[str] = Field(None, max_length=100)
    recipient_name: str = Field(..., max_length=255)
    phone_country_code: Optional[str] = Field(None, max_length=10)
    phone_number: str = Field(..., max_length=32)
    email: Optional[EmailStr] = None
    address_line_1: str = Field(..., max_length=500)
    address_line_2: Optional[str] = Field(None, max_length=500)
    street_number: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    area: Optional[str] = Field(None, max_length=100)
    state_or_province: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    delivery_notes: Optional[str] = Field(None, max_length=1000)


class CustomerAddressCreate(CustomerAddressBase):
    is_default: bool = False


class CustomerAddressUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=100)
    recipient_name: Optional[str] = Field(None, max_length=255)
    phone_country_code: Optional[str] = Field(None, max_length=10)
    phone_number: Optional[str] = Field(None, max_length=32)
    email: Optional[EmailStr] = None
    address_line_1: Optional[str] = Field(None, max_length=500)
    address_line_2: Optional[str] = Field(None, max_length=500)
    street_number: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    area: Optional[str] = Field(None, max_length=100)
    state_or_province: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    delivery_notes: Optional[str] = Field(None, max_length=1000)
    is_default: Optional[bool] = None


class CustomerAddressResponse(CustomerAddressBase):
    id: int
    user_id: int
    is_active: bool
    is_default: bool = False
    location_title: str
    location_subtitle: str
    address_summary: str

    model_config = ConfigDict(from_attributes=True)


class CustomerProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=32)
    phone_country_code: Optional[str] = Field(None, max_length=10)
    phone_national_number: Optional[str] = Field(None, max_length=32)
    avatar_url: Optional[str] = Field(None, max_length=500)
    default_address_id: Optional[int] = None


class PhoneCountryResponse(BaseModel):
    iso2: str
    name: str
    dial_code: str
    flag_emoji: str


class CustomerProfileResponse(BaseModel):
    id: int
    email: Optional[EmailStr]
    phone: Optional[str]
    phone_country_code: Optional[str] = None
    phone_national_number: Optional[str] = None
    phone_display: Optional[str] = None
    phone_is_present: bool = False
    phone_can_edit: bool = True
    phone_country: Optional[PhoneCountryResponse] = None
    full_name: str
    avatar_url: Optional[str]
    status: str
    is_verified: bool
    default_address_id: Optional[int]
    saved_addresses_count: int = 0
    default_address: Optional[CustomerAddressResponse] = None
    total_orders: int = 0
    total_spent: float = 0.0
    loyalty_points: int = 0
    loyalty_points_earned: int = 0
    loyalty_points_redeemed: int = 0

    model_config = ConfigDict(from_attributes=True)
