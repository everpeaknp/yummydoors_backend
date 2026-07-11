from typing import Sequence
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    CustomerAddressCreate,
    CustomerAddressUpdate,
    CustomerProfileUpdate,
    CustomerProfileResponse,
    CustomerAddressResponse,
    PhoneCountryResponse,
)
from app.modules.auth.models import User
from app.modules.customers.models import CustomerAddress
from app.services.cloudinary_service import CloudinaryService
from app.services.avatar_urls import normalize_avatar_url


COUNTRY_BY_DIAL_CODE: dict[str, PhoneCountryResponse] = {
    "+977": PhoneCountryResponse(
        iso2="NP",
        name="Nepal",
        dial_code="+977",
        flag_emoji="🇳🇵",
    ),
    "+91": PhoneCountryResponse(
        iso2="IN",
        name="India",
        dial_code="+91",
        flag_emoji="🇮🇳",
    ),
    "+1": PhoneCountryResponse(
        iso2="US",
        name="United States",
        dial_code="+1",
        flag_emoji="🇺🇸",
    ),
}


class CustomerService:
    def __init__(self, session: AsyncSession):
        self.repository = CustomerRepository(session)

    @staticmethod
    def _build_location_title(address: CustomerAddress) -> str:
        return address.area or address.label or address.city or "Selected location"

    @classmethod
    def _build_location_subtitle(cls, address: CustomerAddress) -> str:
        parts = [
            address.address_line_1.strip() if address.address_line_1 else None,
            address.city.strip() if address.city else None,
            address.state_or_province.strip() if address.state_or_province else None,
        ]
        subtitle = ", ".join(part for part in parts if part)
        return subtitle or cls._build_location_title(address)

    @classmethod
    def _build_address_summary(cls, address: CustomerAddress) -> str:
        parts = [
            address.address_line_1.strip() if address.address_line_1 else None,
            address.street_number.strip() if address.street_number else None,
            address.area.strip() if address.area else None,
            address.city.strip() if address.city else None,
        ]
        summary = ", ".join(part for part in parts if part)
        return summary or cls._build_location_subtitle(address)

    @classmethod
    def _build_address_response(
        cls,
        address: CustomerAddress,
        *,
        default_address_id: int | None,
    ) -> CustomerAddressResponse:
        return CustomerAddressResponse(
            id=address.id,
            user_id=address.user_id,
            label=address.label,
            recipient_name=address.recipient_name,
            phone_country_code=address.phone_country_code,
            phone_number=address.phone_number,
            email=address.email,
            address_line_1=address.address_line_1,
            address_line_2=address.address_line_2,
            street_number=address.street_number,
            city=address.city,
            area=address.area,
            state_or_province=address.state_or_province,
            latitude=address.latitude,
            longitude=address.longitude,
            delivery_notes=address.delivery_notes,
            is_active=address.is_active,
            is_default=default_address_id == address.id,
            location_title=cls._build_location_title(address),
            location_subtitle=cls._build_location_subtitle(address),
            address_summary=cls._build_address_summary(address),
        )

    @staticmethod
    def _clean_phone_part(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = "".join(char for char in value.strip() if char.isdigit() or char == "+")
        return cleaned or None

    @classmethod
    def _compose_phone(cls, country_code: str | None, national_number: str | None) -> str | None:
        clean_country_code = cls._clean_phone_part(country_code)
        clean_national_number = cls._clean_phone_part(national_number)
        if clean_national_number:
            clean_national_number = clean_national_number.lstrip("+")
        if not clean_country_code and not clean_national_number:
            return None
        if not clean_country_code or not clean_country_code.startswith("+"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone country code must start with '+'.",
            )
        if not clean_national_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone national number is required when country code is provided.",
            )
        return f"{clean_country_code}{clean_national_number}"

    @classmethod
    def _parse_phone_metadata(cls, phone: str | None) -> dict:
        clean_phone = cls._clean_phone_part(phone)
        if not clean_phone:
            return {
                "phone_country_code": None,
                "phone_national_number": None,
                "phone_display": None,
                "phone_is_present": False,
                "phone_can_edit": True,
                "phone_country": None,
            }

        for dial_code in sorted(COUNTRY_BY_DIAL_CODE, key=len, reverse=True):
            if clean_phone.startswith(dial_code):
                national_number = clean_phone[len(dial_code):]
                return {
                    "phone_country_code": dial_code,
                    "phone_national_number": national_number,
                    "phone_display": f"{dial_code} {national_number}" if national_number else dial_code,
                    "phone_is_present": True,
                    "phone_can_edit": True,
                    "phone_country": COUNTRY_BY_DIAL_CODE[dial_code],
                }

        return {
            "phone_country_code": None,
            "phone_national_number": clean_phone.lstrip("+"),
            "phone_display": clean_phone,
            "phone_is_present": True,
            "phone_can_edit": True,
            "phone_country": None,
        }

    def _build_profile_response(self, user: User) -> CustomerProfileResponse:
        default_address = None
        active_addresses = [address for address in user.addresses if address.is_active]
        if user.default_address_id:
            default_address = next(
                (address for address in active_addresses if address.id == user.default_address_id),
                None,
            )
        phone_metadata = self._parse_phone_metadata(user.phone)

        return CustomerProfileResponse(
            id=user.id,
            email=user.email,
            phone=user.phone,
            **phone_metadata,
            full_name=user.full_name,
            avatar_url=normalize_avatar_url(user.avatar_url),
            status=user.status,
            is_verified=user.is_verified,
            default_address_id=user.default_address_id,
            saved_addresses_count=len(active_addresses),
            default_address=(
                self._build_address_response(
                    default_address,
                    default_address_id=user.default_address_id,
                )
                if default_address
                else None
            ),
            total_orders=int(user.total_orders or 0),
            total_spent=float(user.total_spent or 0),
            loyalty_points=int(user.loyalty_points or 0),
            loyalty_points_earned=int(user.loyalty_points_earned or 0),
            loyalty_points_redeemed=int(user.loyalty_points_redeemed or 0),
        )

    async def get_profile(self, user_id: int) -> CustomerProfileResponse:
        user = await self.repository.get_user_profile(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            
        return self._build_profile_response(user)

    async def update_profile(self, user_id: int, update_data: CustomerProfileUpdate) -> CustomerProfileResponse:
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_profile(user_id)

        phone_country_code = update_dict.pop("phone_country_code", None)
        phone_national_number = update_dict.pop("phone_national_number", None)
        if phone_country_code is not None or phone_national_number is not None:
            update_dict["phone"] = self._compose_phone(phone_country_code, phone_national_number)

        if "email" in update_dict and update_dict["email"] is not None:
            update_dict["email"] = update_dict["email"].strip().lower()
            existing = await self.repository.get_user_by_email(update_dict["email"])
            if existing and existing.id != user_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already in use.")

        if "phone" in update_dict and update_dict["phone"] is not None:
            update_dict["phone"] = update_dict["phone"].strip()
            existing = await self.repository.get_user_by_phone(update_dict["phone"])
            if existing and existing.id != user_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone is already in use.")

        if "default_address_id" in update_dict and update_dict["default_address_id"] is not None:
            addr = await self.repository.get_address(update_dict["default_address_id"], user_id)
            if not addr:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid address ID")

        user = await self.repository.update_user_profile(user_id, update_dict)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return await self.get_profile(user_id)

    async def upload_avatar(
        self,
        user_id: int,
        file: UploadFile,
        client_scope: str = "mobile",
    ) -> CustomerProfileResponse:
        avatar_url = await CloudinaryService.upload_image(
            file,
            "customers/avatars",
            client_scope=client_scope,
        )
        user = await self.repository.update_user_profile(
            user_id,
            {"avatar_url": normalize_avatar_url(avatar_url)},
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return await self.get_profile(user_id)

    async def soft_delete_account(self, user_id: int) -> dict:
        await self.repository.revoke_refresh_sessions(user_id)
        user = await self.repository.soft_delete_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {"success": True}

    async def list_addresses(self, user_id: int) -> Sequence[CustomerAddressResponse]:
        user = await self.repository.get_user_profile(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        addresses = await self.repository.list_addresses(user_id)
        return [
            self._build_address_response(address, default_address_id=user.default_address_id)
            for address in addresses
        ]

    async def create_address(self, user_id: int, address_data: CustomerAddressCreate) -> CustomerAddressResponse:
        data_dict = address_data.model_dump()
        is_default = data_dict.pop("is_default", False)

        address = await self.repository.create_address(user_id, data_dict)
        address_id = address.id

        if is_default:
            user = await self.repository.update_user_profile(user_id, {"default_address_id": address_id})
            default_address_id = user.default_address_id if user else address_id
        else:
            user = await self.repository.get_user_profile(user_id)
            default_address_id = user.default_address_id if user else None

        await self.repository.session.refresh(address)
        return self._build_address_response(address, default_address_id=default_address_id)

    async def update_address(
        self,
        user_id: int,
        address_id: int,
        update_data: CustomerAddressUpdate,
    ) -> CustomerAddressResponse:
        data_dict = update_data.model_dump(exclude_unset=True)
        is_default = data_dict.pop("is_default", None)

        address = await self.repository.update_address(address_id, user_id, data_dict)
        if not address:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
        address_id_value = address.id

        if is_default is True:
            user = await self.repository.update_user_profile(user_id, {"default_address_id": address_id_value})
            default_address_id = user.default_address_id if user else address_id_value
        elif is_default is False:
            user = await self.repository.get_user_profile(user_id)
            if user and user.default_address_id == address_id_value:
                user = await self.repository.update_user_profile(user_id, {"default_address_id": None})
            default_address_id = user.default_address_id if user else None
        else:
            user = await self.repository.get_user_profile(user_id)
            default_address_id = user.default_address_id if user else None

        await self.repository.session.refresh(address)
        return self._build_address_response(address, default_address_id=default_address_id)

    async def delete_address(self, user_id: int, address_id: int):
        success = await self.repository.delete_address(address_id, user_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    async def set_default_address(self, user_id: int, address_id: int):
        addr = await self.repository.get_address(address_id, user_id)
        if not addr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
            
        await self.repository.update_user_profile(user_id, {"default_address_id": address_id})
