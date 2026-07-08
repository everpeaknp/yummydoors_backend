import pytest

from app.modules.catalog.service import CatalogService
from app.modules.restaurants.schemas import MerchantRestaurantProfileUpdate


class _Role:
    def __init__(self, code: str) -> None:
        self.code = code


class _UserRole:
    def __init__(self, code: str) -> None:
        self.role = _Role(code)


class _ManagedUser:
    def __init__(self) -> None:
        self.roles = [_UserRole("super_admin")]
        self.restaurant_assignments = []


class _Restaurant:
    def __init__(self) -> None:
        self.id = 4
        self.category_links = []


class _CatalogRepositoryStub:
    def __init__(self) -> None:
        self.created_category_payload = None

    async def get_restaurant_with_categories(self, restaurant_id: int):
        return _Restaurant() if restaurant_id == 4 else None

    async def get_category_by_slug(self, slug: str):
        return None

    async def create_category(self, data: dict):
        self.created_category_payload = data
        return type("Category", (), {"id": 99, **data})()

    async def link_category_to_restaurant(self, restaurant_id: int, category_id: int) -> None:
        return None

    async def save(self) -> None:
        return None

    async def refresh(self, instance) -> None:
        return None


def test_merchant_restaurant_profile_update_ignores_admin_only_fields():
    payload = MerchantRestaurantProfileUpdate.model_validate(
        {
            "name": "Ramon Ko Vatti",
            "slug": "should-not-stick",
            "is_featured": True,
        }
    )

    assert payload.model_dump(exclude_unset=True) == {"name": "Ramon Ko Vatti"}


@pytest.mark.asyncio
async def test_create_category_builds_slug_from_name():
    service = CatalogService(session=None)
    service.repository = _CatalogRepositoryStub()

    category = await service.create_category(
        _ManagedUser(),
        4,
        {"name": "Chef Specials"},
    )

    assert category.slug == "chef-specials"
    assert service.repository.created_category_payload == {
        "name": "Chef Specials",
        "slug": "chef-specials",
    }
