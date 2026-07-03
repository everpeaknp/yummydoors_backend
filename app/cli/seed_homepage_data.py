from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable

import app.db.base  # noqa: F401
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.modules.restaurants.models import Category, Restaurant, RestaurantCategory


CATEGORY_FIXTURES = [
    {
        "slug": "all",
        "name": "All",
        "icon_url": None,
        "sort_order": 0,
        "is_featured": True,
        "is_active": True,
    },
    {
        "slug": "momo",
        "name": "Momo",
        "icon_url": None,
        "sort_order": 10,
        "is_featured": True,
        "is_active": True,
    },
    {
        "slug": "coffee",
        "name": "Coffee",
        "icon_url": None,
        "sort_order": 20,
        "is_featured": True,
        "is_active": True,
    },
    {
        "slug": "pizza",
        "name": "Pizza",
        "icon_url": None,
        "sort_order": 30,
        "is_featured": True,
        "is_active": True,
    },
    {
        "slug": "burger",
        "name": "Burger",
        "icon_url": None,
        "sort_order": 40,
        "is_featured": True,
        "is_active": True,
    },
]

RESTAURANT_FIXTURES = [
    {
        "slug": "yummy-momo-house",
        "name": "Yummy Momo House",
        "integration_mode": "external",
        "status": "active",
        "cover_image_url": "https://images.example.com/momo-cover.jpg",
        "logo_url": "https://images.example.com/momo-logo.jpg",
        "short_description": "Steamed momo, thukpa, and quick comfort food.",
        "primary_cuisine_label": "Nepali",
        "city": "Pokhara",
        "area": "Ratnachowk",
        "latitude": 28.2096,
        "longitude": 83.9856,
        "rating_average": 4.6,
        "review_count": 388,
        "supports_delivery": True,
        "has_free_delivery": True,
        "offer_text": "Free delivery on first order",
        "delivery_eta_min_minutes": 20,
        "delivery_eta_max_minutes": 33,
        "sort_rank": 100,
        "is_featured": True,
        "category_slugs": ["all", "momo"],
    },
    {
        "slug": "coffee-break-pokhara",
        "name": "Coffee Break Pokhara",
        "integration_mode": "external",
        "status": "active",
        "cover_image_url": "https://images.example.com/coffee-cover.jpg",
        "logo_url": "https://images.example.com/coffee-logo.jpg",
        "short_description": "Coffee, breakfast, and bakery bites for all-day delivery.",
        "primary_cuisine_label": "Cafe",
        "city": "Pokhara",
        "area": "Lakeside",
        "latitude": 28.2141,
        "longitude": 83.9593,
        "rating_average": 4.3,
        "review_count": 214,
        "supports_delivery": True,
        "has_free_delivery": False,
        "offer_text": "20% off above Rs.500",
        "delivery_eta_min_minutes": 18,
        "delivery_eta_max_minutes": 28,
        "sort_rank": 90,
        "is_featured": True,
        "category_slugs": ["all", "coffee", "burger"],
    },
]


def _apply_fields(
    instance: Category | Restaurant,
    payload: dict[str, object],
    *,
    skip: Iterable[str] = (),
) -> None:
    skip_fields = set(skip)
    for key, value in payload.items():
        if key in skip_fields:
            continue
        setattr(instance, key, value)


async def seed_homepage_data(*, reset: bool) -> None:
    async with AsyncSessionLocal() as session:
        if reset:
            await session.execute(delete(RestaurantCategory))
            await session.execute(delete(Restaurant))
            await session.execute(delete(Category))
            await session.commit()

        category_map: dict[str, Category] = {}
        for payload in CATEGORY_FIXTURES:
            category = await session.scalar(
                select(Category).where(Category.slug == payload["slug"])
            )
            if category is None:
                category = Category(slug=str(payload["slug"]), name=str(payload["name"]))
                session.add(category)
                await session.flush()
            _apply_fields(category, payload)
            category_map[category.slug] = category

        await session.flush()

        for payload in RESTAURANT_FIXTURES:
            restaurant = await session.scalar(
                select(Restaurant).where(Restaurant.slug == payload["slug"])
            )
            if restaurant is None:
                restaurant = Restaurant(slug=str(payload["slug"]), name=str(payload["name"]))
                session.add(restaurant)
                await session.flush()

            _apply_fields(restaurant, payload, skip=("category_slugs",))
            await session.flush()

            await session.execute(
                delete(RestaurantCategory).where(RestaurantCategory.restaurant_id == restaurant.id)
            )
            for category_slug in payload["category_slugs"]:
                category = category_map[category_slug]
                session.add(
                    RestaurantCategory(
                        restaurant_id=restaurant.id,
                        category_id=category.id,
                    )
                )

        await session.commit()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed homepage categories and starter restaurants for YummyDoors."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing homepage categories and restaurants before seeding.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(seed_homepage_data(reset=args.reset))
    print("Homepage seed ready.")


if __name__ == "__main__":
    main()
