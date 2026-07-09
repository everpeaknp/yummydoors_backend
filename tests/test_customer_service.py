import pytest
from io import BytesIO
from fastapi import UploadFile

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
        self.updated_payloads: list[dict] = []
        self.soft_deleted_user_id: int | None = None
        self.revoked_sessions_for_user_id: int | None = None

    async def get_user_by_email(self, email: str):
        return None

    async def get_user_by_phone(self, phone: str):
        return None

    async def get_address(self, address_id: int, user_id: int):
        return None

    async def update_user_profile(self, user_id: int, update_data: dict):
        self.updated_payloads.append(update_data)
        return _ExplodingUser()

    async def get_user_profile(self, user_id: int):
        self.get_user_profile_calls += 1
        return _FreshUser()

    async def revoke_refresh_sessions(self, user_id: int) -> None:
        self.revoked_sessions_for_user_id = user_id

    async def soft_delete_user(self, user_id: int):
        self.soft_deleted_user_id = user_id
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


@pytest.mark.asyncio
async def test_profile_response_contains_phone_country_metadata():
    service = CustomerService(session=None)
    repository = _RepositoryStub()
    service.repository = repository

    response = await service.get_profile(7)

    assert response.phone_country_code == "+977"
    assert response.phone_national_number == "9800000000"
    assert response.phone_display == "+977 9800000000"
    assert response.phone_is_present is True
    assert response.phone_can_edit is True
    assert response.phone_country is not None
    assert response.phone_country.iso2 == "NP"
    assert response.phone_country.flag_emoji == "🇳🇵"


@pytest.mark.asyncio
async def test_update_profile_accepts_country_code_and_national_number():
    service = CustomerService(session=None)
    repository = _RepositoryStub()
    service.repository = repository

    await service.update_profile(
        7,
        CustomerProfileUpdate(
            phone_country_code="+977",
            phone_national_number="9811111111",
        ),
    )

    assert repository.updated_payloads[-1]["phone"] == "+9779811111111"


@pytest.mark.asyncio
async def test_upload_avatar_updates_profile_with_cloudinary_url(monkeypatch):
    from app.modules.customers import service as customer_service_module

    async def fake_upload_image(file: UploadFile, folder_name: str, client_scope: str = "desktop") -> str:
        assert folder_name == "customers/avatars"
        assert client_scope == "mobile"
        return "https://cdn.example.com/customer-avatar.png"

    monkeypatch.setattr(customer_service_module.CloudinaryService, "upload_image", fake_upload_image)

    service = CustomerService(session=None)
    repository = _RepositoryStub()
    service.repository = repository

    upload = UploadFile(file=BytesIO(b"avatar"), filename="avatar.png")
    upload.headers = {"content-type": "image/png"}
    response = await service.upload_avatar(7, upload)

    assert repository.updated_payloads[-1]["avatar_url"] == "https://cdn.example.com/customer-avatar.png"
    assert response.full_name == "Updated Ramon"


@pytest.mark.asyncio
async def test_soft_delete_account_deactivates_user_and_revokes_sessions():
    service = CustomerService(session=None)
    repository = _RepositoryStub()
    service.repository = repository

    result = await service.soft_delete_account(7)

    assert result == {"success": True}
    assert repository.soft_deleted_user_id == 7
    assert repository.revoked_sessions_for_user_id == 7
