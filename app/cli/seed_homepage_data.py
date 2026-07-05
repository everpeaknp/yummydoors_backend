from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable

import app.db.base  # noqa: F401
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.modules.catalog.models import MenuItem
from app.modules.merchandising.models import PromoBanner, PromoPlacement, PromoTargetType
from app.modules.restaurants.models import Category, Restaurant, RestaurantCategory, RestaurantReview


CATEGORY_FIXTURES = [
    {
        "slug": "all",
        "name": "All",
        "icon_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=800&auto=format&fit=crop",
        "sort_order": 0,
        "is_featured": True,
        "is_active": True,
    },
    {
        "slug": "momo",
        "name": "Momo",
        "icon_url": "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?q=80&w=800&auto=format&fit=crop",
        "sort_order": 10,
        "is_featured": True,
        "is_active": True,
    },
    {
        "slug": "coffee",
        "name": "Coffee",
        "icon_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?q=80&w=800&auto=format&fit=crop",
        "sort_order": 20,
        "is_featured": True,
        "is_active": True,
    },
    {
        "slug": "pizza",
        "name": "Pizza",
        "icon_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591?q=80&w=800&auto=format&fit=crop",
        "sort_order": 30,
        "is_featured": True,
        "is_active": True,
    },
    {
        "slug": "burger",
        "name": "Burger",
        "icon_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?q=80&w=800&auto=format&fit=crop",
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
        "cover_image_url": "https://images.unsplash.com/photo-1562967914-608f82629710?q=80&w=1600&auto=format&fit=crop",
        "logo_url": "https://ui-avatars.com/api/?name=Yummy+Momo+House&background=fff3eb&color=f97316&size=256",
        "short_description": "Steamed momo, jhol momo, and late-night comfort bowls.",
        "primary_cuisine_label": "Nepali",
        "city": "Pokhara",
        "area": "Ratnachowk",
        "latitude": 28.2096,
        "longitude": 83.9856,
        "rating_average": 4.6,
        "review_count": 388,
        "supports_delivery": True,
        "has_free_delivery": True,
        "supports_pickup": True,
        "supports_table_booking": False,
        "offer_text": "Free delivery on first order",
        "contact_phone": "+9779800000001",
        "contact_email": "momo@yummydoors.test",
        "opening_time": "09:00",
        "closing_time": "22:30",
        "about_text": "Neighborhood momo kitchen focused on fast delivery, jhol bowls, and family platters.",
        "facilities_text": "Delivery, Pickup, Family portions, Late night",
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
        "cover_image_url": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?q=80&w=1600&auto=format&fit=crop",
        "logo_url": "https://ui-avatars.com/api/?name=Coffee+Break&background=f3f0ea&color=5b3b22&size=256",
        "short_description": "Breakfast plates, espresso, pastries, and quick cafe delivery.",
        "primary_cuisine_label": "Cafe",
        "city": "Pokhara",
        "area": "Lakeside",
        "latitude": 28.2141,
        "longitude": 83.9593,
        "rating_average": 4.3,
        "review_count": 214,
        "supports_delivery": True,
        "has_free_delivery": False,
        "supports_pickup": True,
        "supports_table_booking": True,
        "offer_text": "20% off above Rs.500",
        "contact_phone": "+9779800000002",
        "contact_email": "coffee@yummydoors.test",
        "opening_time": "07:30",
        "closing_time": "21:00",
        "about_text": "Cafe-first restaurant serving coffee, breakfast, and quick pickup for workday orders.",
        "facilities_text": "Delivery, Pickup, Coffee bar, Wi-Fi, Table booking",
        "delivery_eta_min_minutes": 18,
        "delivery_eta_max_minutes": 28,
        "sort_rank": 90,
        "is_featured": True,
        "category_slugs": ["all", "coffee", "burger"],
    },
    {
        "slug": "brick-oven-station",
        "name": "Brick Oven Station",
        "integration_mode": "external",
        "status": "active",
        "cover_image_url": "https://images.unsplash.com/photo-1514326640560-7d063ef2aed5?q=80&w=1600&auto=format&fit=crop",
        "logo_url": "https://ui-avatars.com/api/?name=Brick+Oven&background=fff1e6&color=ea580c&size=256",
        "short_description": "Stone-baked pizzas, garlic bread, and shareable comfort food.",
        "primary_cuisine_label": "Italian",
        "city": "Pokhara",
        "area": "Chipledhunga",
        "latitude": 28.2065,
        "longitude": 83.9892,
        "rating_average": 4.7,
        "review_count": 301,
        "supports_delivery": True,
        "has_free_delivery": False,
        "supports_pickup": True,
        "supports_table_booking": True,
        "offer_text": "Flat Rs.150 off family combos",
        "contact_phone": "+9779800000003",
        "contact_email": "brickoven@yummydoors.test",
        "opening_time": "10:00",
        "closing_time": "23:00",
        "about_text": "Casual pizza and oven grill concept with dine-in, pickup, and shareable platters.",
        "facilities_text": "Delivery, Pickup, Table booking, Wood fired oven, Family seating",
        "delivery_eta_min_minutes": 24,
        "delivery_eta_max_minutes": 36,
        "sort_rank": 80,
        "is_featured": True,
        "category_slugs": ["all", "pizza"],
    },
]

MENU_ITEM_FIXTURES = [
    {
        "restaurant_slug": "yummy-momo-house",
        "category_slug": "momo",
        "slug": "buff-jhol-momo",
        "name": "Buff Jhol Momo",
        "description": "Steamed momo in a spicy sesame-tomato broth.",
        "image_url": "https://images.unsplash.com/photo-1626776876729-bab4369a5a5d?q=80&w=1200&auto=format&fit=crop",
        "price": 240.0,
        "currency_code": "NPR",
        "is_featured": True,
        "is_popular": True,
        "popularity_score": 98,
        "rating_average": 4.8,
        "rating_count": 188,
    },
    {
        "restaurant_slug": "yummy-momo-house",
        "category_slug": "momo",
        "slug": "chicken-kothey-momo",
        "name": "Chicken Kothey Momo",
        "description": "Pan-fried momo with crunchy edges and smoky chutney.",
        "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=1200&auto=format&fit=crop",
        "price": 285.0,
        "currency_code": "NPR",
        "is_featured": True,
        "is_popular": False,
        "popularity_score": 84,
        "rating_average": 4.6,
        "rating_count": 129,
    },
    {
        "restaurant_slug": "coffee-break-pokhara",
        "category_slug": "coffee",
        "slug": "caramel-latte",
        "name": "Caramel Latte",
        "description": "Double-shot espresso with caramel and textured milk.",
        "image_url": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?q=80&w=1200&auto=format&fit=crop",
        "price": 260.0,
        "currency_code": "NPR",
        "is_featured": True,
        "is_popular": True,
        "popularity_score": 91,
        "rating_average": 4.5,
        "rating_count": 96,
    },
    {
        "restaurant_slug": "coffee-break-pokhara",
        "category_slug": "burger",
        "slug": "crispy-chicken-burger",
        "name": "Crispy Chicken Burger",
        "description": "Crunchy chicken fillet, pickles, lettuce, and house sauce.",
        "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?q=80&w=1200&auto=format&fit=crop",
        "price": 390.0,
        "currency_code": "NPR",
        "is_featured": False,
        "is_popular": True,
        "popularity_score": 88,
        "rating_average": 4.4,
        "rating_count": 114,
    },
    {
        "restaurant_slug": "brick-oven-station",
        "category_slug": "pizza",
        "slug": "pepperoni-supreme",
        "name": "Pepperoni Supreme",
        "description": "Wood-fired pizza with pepperoni, mozzarella, and basil oil.",
        "image_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591?q=80&w=1200&auto=format&fit=crop",
        "price": 680.0,
        "currency_code": "NPR",
        "is_featured": True,
        "is_popular": True,
        "popularity_score": 99,
        "rating_average": 4.9,
        "rating_count": 240,
    },
    {
        "restaurant_slug": "brick-oven-station",
        "category_slug": "pizza",
        "slug": "margherita-classic",
        "name": "Margherita Classic",
        "description": "Fresh mozzarella, tomato sauce, and basil on thin crust.",
        "image_url": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?q=80&w=1200&auto=format&fit=crop",
        "price": 540.0,
        "currency_code": "NPR",
        "is_featured": False,
        "is_popular": True,
        "popularity_score": 86,
        "rating_average": 4.7,
        "rating_count": 151,
    },
]

PROMO_FIXTURES = [
    {
        "title": "Free delivery week",
        "subtitle": "Across selected Pokhara favorites",
        "image_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1600&auto=format&fit=crop",
        "placement": PromoPlacement.home_carousel,
        "target_type": PromoTargetType.none,
        "target_id": None,
        "target_url": "/restaurants",
        "cta_text": "Explore now",
        "sort_order": 10,
        "is_active": True,
    },
    {
        "title": "Momo cravings handled",
        "subtitle": "Hot bowls and jhol combos ready in under 30 mins",
        "image_url": "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?q=80&w=1600&auto=format&fit=crop",
        "placement": PromoPlacement.home_carousel,
        "target_type": PromoTargetType.restaurant,
        "target_id_slug": "yummy-momo-house",
        "cta_text": "Order momo",
        "sort_order": 20,
        "is_active": True,
    },
    {
        "title": "Coffee and bakery mornings",
        "subtitle": "Start light, move fast",
        "image_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?q=80&w=1600&auto=format&fit=crop",
        "placement": PromoPlacement.home_banner,
        "target_type": PromoTargetType.restaurant,
        "target_id_slug": "coffee-break-pokhara",
        "cta_text": "See menu",
        "sort_order": 30,
        "is_active": True,
    },
]

REVIEW_FIXTURES = [
    {
        "restaurant_slug": "yummy-momo-house",
        "author_name": "Sanya Sharma",
        "rating": 4.8,
        "comment": "Fast delivery, hot jhol, and the buff momo stayed juicy all the way home.",
    },
    {
        "restaurant_slug": "yummy-momo-house",
        "author_name": "Ritesh Karki",
        "rating": 4.6,
        "comment": "Reliable late-night order. Chutney was properly spicy and packaging was clean.",
    },
    {
        "restaurant_slug": "coffee-break-pokhara",
        "author_name": "Asmita Gurung",
        "rating": 4.4,
        "comment": "Coffee arrived warm and the breakfast plate was good for a quick work morning.",
    },
    {
        "restaurant_slug": "brick-oven-station",
        "author_name": "Aayush Basnet",
        "rating": 4.9,
        "comment": "One of the better pizza deliveries in Pokhara. Crust held up very well.",
    },
]


def _apply_fields(
    instance: Category | Restaurant | MenuItem | PromoBanner,
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
            await session.execute(delete(PromoBanner))
            await session.execute(delete(RestaurantReview))
            await session.execute(delete(MenuItem))
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

        restaurant_map: dict[str, Restaurant] = {}
        for payload in RESTAURANT_FIXTURES:
            restaurant = await session.scalar(
                select(Restaurant).where(Restaurant.slug == payload["slug"])
            )
            if restaurant is None:
                restaurant = Restaurant(slug=str(payload["slug"]), name=str(payload["name"]))
                session.add(restaurant)
                await session.flush()

            _apply_fields(restaurant, payload, skip=("category_slugs",))
            restaurant_map[restaurant.slug] = restaurant
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

        await session.flush()

        for payload in MENU_ITEM_FIXTURES:
            item = await session.scalar(select(MenuItem).where(MenuItem.slug == payload["slug"]))
            restaurant = restaurant_map[str(payload["restaurant_slug"])]
            category = category_map[str(payload["category_slug"])]
            if item is None:
                item = MenuItem(
                    restaurant_id=restaurant.id,
                    category_id=category.id,
                    slug=str(payload["slug"]),
                    name=str(payload["name"]),
                    price=float(payload["price"]),
                )
                session.add(item)
                await session.flush()

            next_payload = dict(payload)
            next_payload["restaurant_id"] = restaurant.id
            next_payload["category_id"] = category.id
            _apply_fields(item, next_payload, skip=("restaurant_slug", "category_slug"))

        await session.flush()

        for payload in PROMO_FIXTURES:
            promo = await session.scalar(
                select(PromoBanner).where(
                    PromoBanner.title == payload["title"],
                    PromoBanner.placement == payload["placement"],
                )
            )
            if promo is None:
                promo = PromoBanner(
                    title=str(payload["title"]),
                    image_url=str(payload["image_url"]),
                )
                session.add(promo)
                await session.flush()

            next_payload = dict(payload)
            target_slug = next_payload.pop("target_id_slug", None)
            if target_slug:
                next_payload["target_id"] = restaurant_map[str(target_slug)].id
            _apply_fields(promo, next_payload)

        await session.flush()

        for payload in REVIEW_FIXTURES:
            restaurant = restaurant_map[str(payload["restaurant_slug"])]
            existing = await session.scalar(
                select(RestaurantReview).where(
                    RestaurantReview.restaurant_id == restaurant.id,
                    RestaurantReview.author_name == payload["author_name"],
                )
            )
            if existing is None:
                existing = RestaurantReview(
                    restaurant_id=restaurant.id,
                    author_name=str(payload["author_name"]),
                    rating=float(payload["rating"]),
                )
                session.add(existing)
                await session.flush()

            _apply_fields(existing, payload, skip=("restaurant_slug",))

        await session.commit()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed homepage categories, restaurants, promos, and menu items for YummyDoors."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing homepage categories, restaurants, menu items, and promos before seeding.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(seed_homepage_data(reset=args.reset))
    print("Homepage seed ready.")


if __name__ == "__main__":
    main()
