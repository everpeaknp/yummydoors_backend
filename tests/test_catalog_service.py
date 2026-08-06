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
    def __init__(self, *, existing_category=None, categories=None) -> None:
        self.created_category_payload = None
        self.existing_category = existing_category
        self.categories = categories or []
        self.linked: list[tuple[int, int]] = []

    async def get_restaurant_with_categories(self, restaurant_id: int):
        return _Restaurant() if restaurant_id == 4 else None

    async def get_category_by_slug(self, slug: str):
        if self.existing_category is not None and self.existing_category.slug == slug:
            return self.existing_category
        return None

    async def get_category_by_id(self, category_id: int):
        for category in self.categories:
            if category.id == category_id:
                return category
        return None

    async def create_category(self, data: dict):
        self.created_category_payload = data
        return type("Category", (), {"id": 99, **data})()

    async def link_category_to_restaurant(self, restaurant_id: int, category_id: int) -> None:
        self.linked.append((restaurant_id, category_id))

    async def list_categories(self):
        return self.categories

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


@pytest.mark.asyncio
async def test_create_category_links_existing_match_instead_of_duplicating():
    existing = type("Category", (), {"id": 7, "name": "Pizza", "slug": "pizza"})()
    service = CatalogService(session=None)
    service.repository = _CatalogRepositoryStub(existing_category=existing)

    category = await service.create_category(_ManagedUser(), 4, {"name": "Pizza"})

    assert category is existing
    assert service.repository.created_category_payload is None
    assert service.repository.linked == [(4, 7)]


@pytest.mark.asyncio
async def test_list_all_categories_returns_full_platform_catalog():
    categories = [
        type("Category", (), {"id": 1, "name": "Pizza", "slug": "pizza"})(),
        type("Category", (), {"id": 2, "name": "Burger", "slug": "burger"})(),
    ]
    service = CatalogService(session=None)
    service.repository = _CatalogRepositoryStub(categories=categories)

    result = await service.list_all_categories(_ManagedUser(), 4)

    assert result == categories


@pytest.mark.asyncio
async def test_link_existing_category_attaches_without_creating():
    existing = type("Category", (), {"id": 7, "name": "Pizza", "slug": "pizza"})()
    service = CatalogService(session=None)
    service.repository = _CatalogRepositoryStub(categories=[existing])

    category = await service.link_existing_category(_ManagedUser(), 4, 7)

    assert category is existing
    assert service.repository.linked == [(4, 7)]
    assert service.repository.created_category_payload is None


@pytest.mark.asyncio
async def test_link_existing_category_404s_when_category_missing():
    from fastapi import HTTPException

    service = CatalogService(session=None)
    service.repository = _CatalogRepositoryStub()

    with pytest.raises(HTTPException) as exc_info:
        await service.link_existing_category(_ManagedUser(), 4, 999)

    assert exc_info.value.status_code == 404
