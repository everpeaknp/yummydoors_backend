import pytest

from app.modules.customers.schemas import CustomerProfileUpdate
from app.modules.customers.service import CustomerService


class _ExplodingUser:
    def __init__(self) -> None:
        self.id = 7
        self.email = "ramon@example.com"
        self.phone = "+9779800000000"
        self.full_name = "Updated Ramon"
        self.avatar_url = None
        self.status = "active"
        self.is_verified = True
        self.default_address_id = 11

    @property
    def addresses(self):  # pragma: no cover - this is the failure trigger
        raise RuntimeError("stale relationship access")


class _FreshAddress:
    id = 11
    user_id = 7
    label = "Home"
    recipient_name = "Ramon"
    phone_country_code = "+977"
    phone_number = "9800000000"
    email = "ramon@example.com"
    address_line_1 = "Lakeside"
    address_line_2 = None
    street_number = None
    city = "Pokhara"
    area = "Lakeside"
    state_or_province = "Gandaki"
    latitude = 28.2096
    longitude = 83.9856
    delivery_notes = None
    is_active = True


class _FreshUser:
    id = 7
    email = "ramon@example.com"
    phone = "+9779800000000"
    full_name = "Updated Ramon"
    avatar_url = None
    status = "active"
    is_verified = True
    default_address_id = 11
    addresses = [_FreshAddress()]


class _RepositoryStub:
    def __init__(self) -> None:
        self.get_user_profile_calls = 0

    async def get_user_by_email(self, email: str):
        return None

    async def get_user_by_phone(self, phone: str):
        return None

    async def get_address(self, address_id: int, user_id: int):
        return None

    async def update_user_profile(self, user_id: int, update_data: dict):
        return _ExplodingUser()

    async def get_user_profile(self, user_id: int):
        self.get_user_profile_calls += 1
        return _FreshUser()


@pytest.mark.asyncio
async def test_update_profile_reloads_profile_after_update():
    service = CustomerService(session=None)
    repository = _RepositoryStub()
    service.repository = repository

    response = await service.update_profile(
        7,
        CustomerProfileUpdate(full_name="Updated Ramon"),
    )

    assert response.full_name == "Updated Ramon"
    assert response.saved_addresses_count == 1
    assert response.default_address is not None
    assert response.default_address.location_title == "Lakeside"
    assert repository.get_user_profile_calls == 1
