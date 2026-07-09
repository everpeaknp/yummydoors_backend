from __future__ import annotations

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.models import FoodType, MenuItem
from app.modules.orders.models import Order, OrderStatus
from app.modules.restaurants.models import (
    Category,
    Restaurant,
    RestaurantCategory,
    RestaurantGalleryImage,
    RestaurantReview,
    RestaurantReviewImage,
)


class RestaurantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _restaurant_query(self) -> Select[tuple[Restaurant]]:
        return (
            select(Restaurant)
            .options(
                selectinload(Restaurant.category_links).selectinload(RestaurantCategory.category),
                selectinload(Restaurant.gallery_images),
            )
            .where(Restaurant.status == "active")
            .order_by(
                Restaurant.sort_rank.desc(), Restaurant.rating_average.desc(), Restaurant.id.asc()
            )
        )

    async def list_restaurants(
        self,
        *,
        search: str | None = None,
        category_slug: str | None = None,
        food_type: FoodType | None = None,
        supports_delivery: bool | None = None,
        supports_pickup: bool | None = None,
        has_free_delivery: bool | None = None,
        featured_only: bool | None = None,
        sort_by: str | None = None,
    ) -> list[Restaurant]:
        stmt = self._restaurant_query()

        if category_slug:
            stmt = (
                stmt.join(
                    RestaurantCategory,
                    RestaurantCategory.restaurant_id == Restaurant.id,
                )
                .join(Category, Category.id == RestaurantCategory.category_id)
                .where(Category.slug == category_slug)
            )

        if search or food_type:
            stmt = stmt.outerjoin(MenuItem, MenuItem.restaurant_id == Restaurant.id)

        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Restaurant.name).like(term),
                    func.lower(func.coalesce(Restaurant.short_description, "")).like(term),
                    func.lower(func.coalesce(Restaurant.primary_cuisine_label, "")).like(term),
                    func.lower(func.coalesce(MenuItem.name, "")).like(term),
                    func.lower(func.coalesce(MenuItem.description, "")).like(term),
                )
            )

        if food_type:
            stmt = stmt.where(MenuItem.food_type == food_type)

        if supports_delivery is not None:
            stmt = stmt.where(Restaurant.supports_delivery.is_(supports_delivery))
        if supports_pickup is not None:
            stmt = stmt.where(Restaurant.supports_pickup.is_(supports_pickup))
        if has_free_delivery is not None:
            stmt = stmt.where(Restaurant.has_free_delivery.is_(has_free_delivery))
        if featured_only:
            stmt = stmt.where(Restaurant.is_featured.is_(True))

        if sort_by == "rating":
            stmt = stmt.order_by(
                Restaurant.rating_average.desc(),
                Restaurant.review_count.desc(),
                Restaurant.id.asc(),
            )
        elif sort_by == "delivery_time":
            stmt = stmt.order_by(
                Restaurant.delivery_eta_min_minutes.asc().nullslast(), Restaurant.id.asc()
            )
        elif sort_by == "highly_reordered":
            popularity_rank = (
                select(func.max(func.coalesce(MenuItem.popularity_score, 0)))
                .where(MenuItem.restaurant_id == Restaurant.id)
                .correlate(Restaurant)
                .scalar_subquery()
            )
            stmt = stmt.order_by(popularity_rank.desc().nullslast(), Restaurant.id.asc())
        else:
            stmt = stmt.order_by(
                Restaurant.sort_rank.desc(), Restaurant.rating_average.desc(), Restaurant.id.asc()
            )

        result = await self.db.execute(stmt.distinct())
        return list(result.scalars().unique().all())

    async def get_restaurant_by_slug(self, slug: str) -> Restaurant | None:
        result = await self.db.execute(self._restaurant_query().where(Restaurant.slug == slug))
        return result.scalars().unique().first()

    async def count_restaurants(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Restaurant).where(Restaurant.status == "active")
        )
        return int(result.scalar_one() or 0)

    async def list_popular_restaurants(self, limit: int = 12) -> list[Restaurant]:
        """Restaurants ranked by total delivered order count — powers the Explore section."""
        order_count_sub = (
            select(func.count(Order.id))
            .where(
                Order.restaurant_id == Restaurant.id,
                Order.status == OrderStatus.delivered,
            )
            .correlate(Restaurant)
            .scalar_subquery()
        )
        stmt = (
            self._restaurant_query()
            .order_by(
                order_count_sub.desc(),
                Restaurant.rating_average.desc(),
                Restaurant.id.asc(),
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def search_restaurants(
        self, *, query: str, limit: int = 12
    ) -> list[tuple[Restaurant, list[MenuItem]]]:
        term = f"%{query.strip().lower()}%"
        restaurant_stmt = (
            self._restaurant_query()
            .outerjoin(MenuItem, MenuItem.restaurant_id == Restaurant.id)
            .where(
                or_(
                    func.lower(Restaurant.name).like(term),
                    func.lower(func.coalesce(Restaurant.short_description, "")).like(term),
                    func.lower(func.coalesce(MenuItem.name, "")).like(term),
                    func.lower(func.coalesce(MenuItem.description, "")).like(term),
                )
            )
            .limit(limit)
            .distinct()
        )
        restaurants = list((await self.db.execute(restaurant_stmt)).scalars().unique().all())
        if not restaurants:
            return []

        restaurant_ids = [restaurant.id for restaurant in restaurants]
        menu_stmt = (
            select(MenuItem)
            .where(
                MenuItem.restaurant_id.in_(restaurant_ids),
                or_(
                    func.lower(MenuItem.name).like(term),
                    func.lower(func.coalesce(MenuItem.description, "")).like(term),
                ),
            )
            .order_by(MenuItem.popularity_score.desc(), MenuItem.id.asc())
        )
        menu_items = list((await self.db.execute(menu_stmt)).scalars().all())
        items_by_restaurant: dict[int, list[MenuItem]] = {
            restaurant_id: [] for restaurant_id in restaurant_ids
        }
        for item in menu_items:
            items_by_restaurant.setdefault(item.restaurant_id, []).append(item)

        return [
            (restaurant, items_by_restaurant.get(restaurant.id, [])[:4])
            for restaurant in restaurants
        ]

    async def list_featured_categories(self) -> list[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.is_active.is_(True), Category.is_featured.is_(True))
            .order_by(Category.sort_order.asc(), Category.id.asc())
        )
        return list(result.scalars().all())

    async def list_related_restaurants(
        self, restaurant: Restaurant, limit: int = 6
    ) -> list[Restaurant]:
        category_ids = [
            link.category_id for link in restaurant.category_links if link.category_id is not None
        ]
        if not category_ids:
            return []

        stmt = (
            self._restaurant_query()
            .join(RestaurantCategory, RestaurantCategory.restaurant_id == Restaurant.id)
            .where(
                Restaurant.id != restaurant.id,
                RestaurantCategory.category_id.in_(category_ids),
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_reviews(self, restaurant_id: int, limit: int = 20) -> list[RestaurantReview]:
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.images))
            .where(
                and_(
                    RestaurantReview.restaurant_id == restaurant_id,
                    RestaurantReview.is_published.is_(True),
                )
            )
            .order_by(RestaurantReview.created_at.desc(), RestaurantReview.id.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_review_by_id(self, restaurant_id: int, review_id: int) -> RestaurantReview | None:
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.images))
            .where(
                and_(
                    RestaurantReview.restaurant_id == restaurant_id,
                    RestaurantReview.id == review_id,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_review_by_user(self, restaurant_id: int, user_id: int) -> RestaurantReview | None:
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.images))
            .where(
                and_(
                    RestaurantReview.restaurant_id == restaurant_id,
                    RestaurantReview.user_id == user_id,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_review_by_order(self, order_id: int) -> RestaurantReview | None:
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.images))
            .where(RestaurantReview.order_id == order_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def has_delivered_order(self, restaurant_id: int, user_id: int) -> bool:
        stmt = (
            select(Order.id)
            .where(
                and_(
                    Order.restaurant_id == restaurant_id,
                    Order.customer_id == user_id,
                    Order.status == OrderStatus.delivered,
                )
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_review(
        self,
        *,
        restaurant_id: int,
        user_id: int,
        author_name: str,
        rating: float,
        comment: str | None,
        order_id: int | None = None,
        image_urls: list[str] | None = None,
    ) -> RestaurantReview:
        review = RestaurantReview(
            restaurant_id=restaurant_id,
            user_id=user_id,
            author_name=author_name,
            rating=rating,
            comment=comment,
            order_id=order_id,
            source="yummydoors",
            is_published=True,
        )
        self.db.add(review)
        await self.db.flush()  # get review.id before committing

        if image_urls:
            for idx, url in enumerate(image_urls[:5]):
                self.db.add(
                    RestaurantReviewImage(review_id=review.id, image_url=url, sort_order=idx)
                )

        await self.db.commit()
        await self.db.refresh(review)
        # Eagerly load images after refresh
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.images))
            .where(RestaurantReview.id == review.id)
        )
        result = await self.db.execute(stmt)
        loaded = result.scalars().first()
        return loaded or review

    async def update_review(
        self,
        review: RestaurantReview,
        *,
        rating: float | None,
        comment: str | None,
        image_urls: list[str] | None = None,
    ) -> RestaurantReview:
        if rating is not None:
            review.rating = rating
        if comment is not None:
            review.comment = comment
        review.is_published = True

        if image_urls is not None:
            # Replace all images
            for img in list(review.images):
                await self.db.delete(img)
            await self.db.flush()
            for idx, url in enumerate(image_urls[:5]):
                self.db.add(
                    RestaurantReviewImage(review_id=review.id, image_url=url, sort_order=idx)
                )

        await self.db.commit()
        # Re-load with images
        stmt = (
            select(RestaurantReview)
            .options(selectinload(RestaurantReview.images))
            .where(RestaurantReview.id == review.id)
        )
        result = await self.db.execute(stmt)
        loaded = result.scalars().first()
        return loaded or review

    async def delete_review(self, review: RestaurantReview) -> None:
        await self.db.delete(review)
        await self.db.commit()

    async def sync_review_stats(self, restaurant_id: int) -> None:
        stats_stmt = select(
            func.count(RestaurantReview.id),
            func.coalesce(func.avg(RestaurantReview.rating), 0.0),
        ).where(
            and_(
                RestaurantReview.restaurant_id == restaurant_id,
                RestaurantReview.is_published.is_(True),
            )
        )
        count_value, average_value = (await self.db.execute(stats_stmt)).one()

        restaurant = await self.get_restaurant_by_id(restaurant_id)
        if restaurant is None:
            return

        restaurant.review_count = int(count_value or 0)
        restaurant.rating_average = round(float(average_value or 0.0), 2)
        await self.db.commit()

    async def get_restaurant_by_id(self, restaurant_id: int) -> Restaurant | None:
        result = await self.db.execute(
            self._restaurant_query().where(Restaurant.id == restaurant_id)
        )
        return result.scalars().unique().first()

    # ── Gallery ──────────────────────────────────────────────────────────────

    async def list_gallery_images(self, restaurant_id: int) -> list[RestaurantGalleryImage]:
        stmt = (
            select(RestaurantGalleryImage)
            .where(RestaurantGalleryImage.restaurant_id == restaurant_id)
            .order_by(RestaurantGalleryImage.sort_order.asc(), RestaurantGalleryImage.id.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_gallery_image_by_id(
        self, restaurant_id: int, image_id: int
    ) -> RestaurantGalleryImage | None:
        stmt = select(RestaurantGalleryImage).where(
            and_(
                RestaurantGalleryImage.restaurant_id == restaurant_id,
                RestaurantGalleryImage.id == image_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def add_gallery_image(
        self,
        *,
        restaurant_id: int,
        image_url: str,
        caption: str | None = None,
        sort_order: int = 0,
    ) -> RestaurantGalleryImage:
        image = RestaurantGalleryImage(
            restaurant_id=restaurant_id,
            image_url=image_url,
            caption=caption,
            sort_order=sort_order,
        )
        self.db.add(image)
        await self.db.commit()
        await self.db.refresh(image)
        return image

    async def delete_gallery_image(self, image: RestaurantGalleryImage) -> None:
        await self.db.delete(image)
        await self.db.commit()
