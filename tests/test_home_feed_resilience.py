from types import SimpleNamespace

import pytest

from app.modules.merchandising.service import MerchandisingService
from app.modules.restaurants.api import build_safe_menu_item_summaries


def test_home_feed_skips_invalid_menu_items_instead_of_crashing():
    valid = SimpleNamespace(
        id=1,
        restaurant_id=10,
        category_id=None,
        slug="buff-momo",
        name="Buff Momo",
        description=None,
        image_url=None,
        price=240.0,
        currency_code="NPR",
        is_available=True,
        food_type=None,
        is_spicy=False,
        is_featured=False,
        is_popular=True,
        popularity_score=10,
        rating_average=0.0,
        rating_count=0,
        is_favorited=False,
        modifier_groups=[],
    )
    invalid = SimpleNamespace(
        id=2,
        restaurant_id=10,
        category_id=None,
        slug=None,
        name="Broken Item",
        description=None,
        image_url=None,
        price=100.0,
        currency_code="NPR",
        is_available=True,
        food_type=None,
        is_spicy=False,
        is_featured=False,
        is_popular=False,
        popularity_score=0,
        rating_average=0.0,
        rating_count=0,
        is_favorited=False,
        modifier_groups=[],
    )

    result = build_safe_menu_item_summaries(
        [valid, invalid],
        section="popular_foods",
    )

    assert len(result) == 1
    assert result[0].slug == "buff-momo"


def test_merchandising_service_skips_invalid_promos_instead_of_crashing():
    service = MerchandisingService(session=None)  # type: ignore[arg-type]
    valid = SimpleNamespace(
        id=1,
        title="Promo",
        subtitle=None,
        image_url="https://cdn.example.com/promo.jpg",
        image_url_mobile=None,
        placement="home_banner",
        target_type="none",
        target_id=None,
        target_url=None,
        cta_text=None,
        sort_order=0,
        is_active=True,
        start_at=None,
        end_at=None,
    )
    invalid = SimpleNamespace(
        id=2,
        title="Broken Promo",
        subtitle=None,
        image_url=None,
        image_url_mobile=None,
        placement="home_banner",
        target_type="none",
        target_id=None,
        target_url=None,
        cta_text=None,
        sort_order=0,
        is_active=True,
        start_at=None,
        end_at=None,
    )

    result = service._safe_validate_many(  # noqa: SLF001 - intentional unit coverage
        model=__import__(
            "app.modules.merchandising.schemas",
            fromlist=["PromoBannerResponse"],
        ).PromoBannerResponse,
        rows=[valid, invalid],
        section="active_promos",
    )

    assert len(result) == 1
    assert result[0].title == "Promo"
