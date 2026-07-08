from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.favorites.api import (
    build_safe_favorite_menu_items,
    favorite_menu_item,
    unfavorite_menu_item,
)


class _User:
    id = 7


class _Restaurant:
    id = 1
    slug = "ramon-ko-vatti"
    name = "Ramon ko vatti"
    cover_image_url = None
    logo_url = None
    short_description = None
    primary_cuisine_label = "Nepali"
    city = "Pokhara"
    area = "Lakeside"
    rating_average = 4.5
    review_count = 12
    supports_delivery = True
    has_free_delivery = False
    supports_pickup = True
    supports_table_booking = False
    offer_text = None
    contact_phone = None
    contact_email = None
    delivery_eta_min_minutes = 25
    delivery_eta_max_minutes = 40
    opening_time = None
    closing_time = None
    is_featured = False
    latitude = None
    longitude = None
    category_links = []


class _MenuItem:
    id = 2
    restaurant_id = 1
    category_id = None
    slug = "buff-jhol-momo"
    name = "Buff Jhol Momo"
    description = "Steamed momo"
    image_url = None
    price = 240
    currency_code = "NPR"
    is_available = True
    food_type = None
    is_spicy = False
    is_featured = False
    is_popular = False
    popularity_score = 0
    rating_average = 0
    rating_count = 0
    restaurant = _Restaurant()


class _Favorite:
    id = 11
    menu_item_id = 2
    created_at = None


class _Repo:
    db = None

    def __init__(self, *, menu_item=None, favorite=None) -> None:
        self.menu_item = menu_item
        self.favorite = favorite
        self.deleted = False

    async def get_menu_item(self, menu_item_id: int):
        return self.menu_item

    async def get_menu_item_favorite(self, user_id: int, menu_item_id: int):
        return self.favorite

    async def add_menu_item_favorite(self, user_id: int, menu_item_id: int):
        self.favorite = _Favorite()
        return self.favorite

    async def delete_menu_item_favorite(self, favorite) -> None:
        self.deleted = True


@pytest.mark.asyncio
async def test_favorite_menu_item_missing_target_returns_404_not_400():
    with pytest.raises(HTTPException) as exc:
        await favorite_menu_item(999, current_user=_User(), repo=_Repo(menu_item=None))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Menu item not found."


@pytest.mark.asyncio
async def test_favorite_menu_item_existing_favorite_is_idempotent():
    response = await favorite_menu_item(
        2,
        current_user=_User(),
        repo=_Repo(menu_item=_MenuItem(), favorite=_Favorite()),
    )

    assert response.status == "success"
    assert response.data.menu_item.id == 2


@pytest.mark.asyncio
async def test_unfavorite_menu_item_missing_favorite_is_idempotent():
    response = await unfavorite_menu_item(2, current_user=_User(), repo=_Repo(favorite=None))

    assert response.status == "success"
    assert response.data == {"menu_item_id": 2}


def test_build_safe_favorite_menu_items_skips_invalid_rows():
    valid_menu_item = _MenuItem()
    invalid_menu_item = SimpleNamespace(
        id=3,
        restaurant_id=1,
        category_id=None,
        slug=None,
        name="Broken Item",
        description=None,
        image_url=None,
        price=120,
        currency_code="NPR",
        is_available=True,
        food_type=None,
        is_spicy=False,
        is_featured=False,
        is_popular=False,
        popularity_score=0,
        rating_average=0,
        rating_count=0,
        modifier_groups=[],
        restaurant=_Restaurant(),
    )

    rows = [
        SimpleNamespace(
            id=11,
            created_at=type("CreatedAt", (), {"isoformat": lambda self: "2026-07-08T00:00:00"})(),
            menu_item=valid_menu_item,
        ),
        SimpleNamespace(
            id=12,
            created_at=type("CreatedAt", (), {"isoformat": lambda self: "2026-07-08T00:00:00"})(),
            menu_item=invalid_menu_item,
        ),
    ]

    result = build_safe_favorite_menu_items(rows)

    assert len(result) == 1
    assert result[0].menu_item.id == 2
