import re

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import MenuItemResponse, MenuItemSummary
from app.modules.auth.models import User
from app.modules.merchandising.schemas import MerchantPromoCreate, MerchantPromoUpdate, PromoBannerResponse
from app.modules.restaurants.schemas import (
    CategorySummary,
    MerchantRestaurantProfileResponse,
    MerchantRestaurantProfileUpdate,
)

class CatalogService:
    def __init__(self, session: AsyncSession):
        self.repository = CatalogRepository(session)

    async def get_restaurant_menu(self, restaurant_id: int) -> list[MenuItemResponse]:
        items = await self.repository.get_menu_by_restaurant(restaurant_id)
        return [MenuItemResponse.model_validate(item) for item in items]

    async def get_menu_item_by_slug(self, slug: str) -> MenuItemResponse | None:
        item = await self.repository.get_menu_item_by_slug(slug)
        if not item:
            return None
        return MenuItemResponse.model_validate(item)

    def _can_manage_restaurant(self, user: User, restaurant_id: int) -> bool:
        role_codes = {user_role.role.code for user_role in user.roles}
        if role_codes.intersection({"super_admin", "ops_admin"}):
            return True
        return any(
            assignment.restaurant_id == restaurant_id and assignment.assignment_type == "owner"
            for assignment in user.restaurant_assignments
        )

    async def _require_managed_restaurant(self, user: User, restaurant_id: int):
        if not self._can_manage_restaurant(user, restaurant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to manage this restaurant.",
            )
        restaurant = await self.repository.get_restaurant_with_categories(restaurant_id)
        if restaurant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
        return restaurant

    async def get_merchant_restaurant_profile(
        self,
        user: User,
        restaurant_id: int,
    ) -> MerchantRestaurantProfileResponse:
        restaurant = await self._require_managed_restaurant(user, restaurant_id)
        categories = [
            CategorySummary.model_validate(link.category)
            for link in sorted(
                restaurant.category_links,
                key=lambda item: (item.category.sort_order, item.category.id),
            )
            if link.category is not None
        ]
        return MerchantRestaurantProfileResponse(
            id=restaurant.id,
            name=restaurant.name,
            slug=restaurant.slug,
            integration_mode=restaurant.integration_mode,
            status=restaurant.status,
            cover_image_url=restaurant.cover_image_url,
            logo_url=restaurant.logo_url,
            short_description=restaurant.short_description,
            primary_cuisine_label=restaurant.primary_cuisine_label,
            city=restaurant.city,
            area=restaurant.area,
            latitude=restaurant.latitude,
            longitude=restaurant.longitude,
            rating_average=restaurant.rating_average,
            review_count=restaurant.review_count,
            supports_delivery=restaurant.supports_delivery,
            has_free_delivery=restaurant.has_free_delivery,
            supports_pickup=restaurant.supports_pickup,
            supports_table_booking=restaurant.supports_table_booking,
            offer_text=restaurant.offer_text,
            contact_phone=restaurant.contact_phone,
            contact_email=restaurant.contact_email,
            opening_time=restaurant.opening_time,
            closing_time=restaurant.closing_time,
            about_text=restaurant.about_text,
            facilities_text=restaurant.facilities_text,
            delivery_eta_min_minutes=restaurant.delivery_eta_min_minutes,
            delivery_eta_max_minutes=restaurant.delivery_eta_max_minutes,
            sort_rank=restaurant.sort_rank,
            is_featured=restaurant.is_featured,
            categories=categories,
        )

    async def update_merchant_restaurant_profile(
        self,
        user: User,
        restaurant_id: int,
        payload: MerchantRestaurantProfileUpdate,
    ) -> MerchantRestaurantProfileResponse:
        restaurant = await self._require_managed_restaurant(user, restaurant_id)
        data = payload.model_dump(exclude_unset=True, exclude={"category_ids"})
        for key, value in data.items():
            setattr(restaurant, key, value)

        if payload.category_ids is not None:
            existing_links = {link.category_id for link in restaurant.category_links}
            desired_ids = set(payload.category_ids)
            for category_id in desired_ids:
                category = await self.repository.get_category_by_id(category_id)
                if category is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown category id: {category_id}",
                    )
                if category_id not in existing_links:
                    await self.repository.link_category_to_restaurant(restaurant.id, category_id)

            for category_id in existing_links - desired_ids:
                await self.repository.null_menu_item_category_for_restaurant(restaurant.id, category_id)
                await self.repository.unlink_category_from_restaurant(restaurant.id, category_id)

        await self.repository.save()
        return await self.get_merchant_restaurant_profile(user, restaurant_id)

    async def _build_unique_category_slug(self, value: str) -> str:
        return await self._build_unique_slug(value, lookup=self.repository.get_category_by_slug, fallback="category")

    async def _build_unique_menu_item_slug(self, value: str) -> str:
        return await self._build_unique_slug(value, lookup=self.repository.get_menu_item_by_slug, fallback="item")

    async def _build_unique_slug(self, value: str, *, lookup, fallback: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or fallback
        candidate = slug
        counter = 2
        while await lookup(candidate) is not None:
            candidate = f"{slug}-{counter}"
            counter += 1
        return candidate

    async def create_category(self, user: User, restaurant_id: int, data: dict):
        await self._require_managed_restaurant(user, restaurant_id)
        name = (data.get("name") or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name is required.",
            )
        slug = await self._build_unique_category_slug(name)
        data = {"name": name, "slug": slug}
        existing = await self.repository.get_category_by_slug(data["slug"])
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this slug already exists.",
            )
        category = await self.repository.create_category(data)
        await self.repository.link_category_to_restaurant(restaurant_id, category.id)
        await self.repository.save()
        await self.repository.refresh(category)
        return category

    async def update_category(self, user: User, restaurant_id: int, category_id: int, data: dict):
        await self._require_managed_restaurant(user, restaurant_id)
        if not await self.repository.is_category_linked_to_restaurant(restaurant_id, category_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found in this restaurant.",
            )
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()
            if not data["name"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category name cannot be empty.",
                )
        category = await self.repository.update_category(category_id, data)
        if not category:
            return None
        await self.repository.save()
        await self.repository.refresh(category)
        return category

    async def delete_category(self, user: User, restaurant_id: int, category_id: int) -> bool:
        await self._require_managed_restaurant(user, restaurant_id)
        if not await self.repository.is_category_linked_to_restaurant(restaurant_id, category_id):
            return False
        await self.repository.null_menu_item_category_for_restaurant(restaurant_id, category_id)
        await self.repository.unlink_category_from_restaurant(restaurant_id, category_id)
        if await self.repository.category_link_count(category_id) == 0:
            await self.repository.delete_category(category_id)
        await self.repository.save()
        return True

    async def list_categories(self, user: User, restaurant_id: int):
        await self._require_managed_restaurant(user, restaurant_id)
        return await self.repository.list_restaurant_categories(restaurant_id)

    async def list_merchant_menu_items(self, user: User, restaurant_id: int) -> list[MenuItemResponse]:
        await self._require_managed_restaurant(user, restaurant_id)
        items = await self.repository.get_menu_by_restaurant(restaurant_id)
        return [MenuItemResponse.model_validate(item) for item in items]

    async def create_menu_item(self, user: User, restaurant_id: int, data: dict) -> MenuItemSummary:
        await self._require_managed_restaurant(user, restaurant_id)
        name = (data.get("name") or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Menu item name is required.",
            )
        data["name"] = name
        provided_slug = (data.get("slug") or "").strip()
        data["slug"] = provided_slug or await self._build_unique_menu_item_slug(name)
        category_id = data.get("category_id")
        if category_id is not None and not await self.repository.is_category_linked_to_restaurant(
            restaurant_id, category_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected category does not belong to this restaurant.",
            )
        item = await self.repository.create_menu_item(restaurant_id, data)
        await self.repository.save()
        await self.repository.refresh(item)
        return MenuItemSummary.model_validate(item)

    async def update_menu_item(
        self,
        user: User,
        restaurant_id: int,
        item_id: int,
        data: dict,
    ) -> MenuItemSummary | None:
        await self._require_managed_restaurant(user, restaurant_id)
        item = await self.repository.get_menu_item_by_id(item_id)
        if item is None or item.restaurant_id != restaurant_id:
            return None
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()
            if not data["name"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Menu item name cannot be empty.",
                )
        category_id = data.get("category_id")
        if category_id is not None and not await self.repository.is_category_linked_to_restaurant(
            restaurant_id, category_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected category does not belong to this restaurant.",
            )
        item = await self.repository.update_menu_item(item_id, data)
        if not item:
            return None
        await self.repository.save()
        await self.repository.refresh(item)
        return MenuItemSummary.model_validate(item)

    async def delete_menu_item(self, user: User, restaurant_id: int, item_id: int) -> bool:
        await self._require_managed_restaurant(user, restaurant_id)
        item = await self.repository.get_menu_item_by_id(item_id)
        if item is None or item.restaurant_id != restaurant_id:
            return False
        success = await self.repository.delete_menu_item(item_id)
        if success:
            await self.repository.save()
        return success

    async def list_restaurant_promos(self, user: User, restaurant_id: int) -> list[PromoBannerResponse]:
        await self._require_managed_restaurant(user, restaurant_id)
        promos = await self.repository.list_restaurant_promos(restaurant_id)
        return [PromoBannerResponse.model_validate(promo) for promo in promos]

    async def create_restaurant_promo(
        self,
        user: User,
        restaurant_id: int,
        payload: MerchantPromoCreate,
    ) -> PromoBannerResponse:
        await self._require_managed_restaurant(user, restaurant_id)
        promo = await self.repository.create_restaurant_promo(restaurant_id, payload.model_dump())
        await self.repository.save()
        await self.repository.refresh(promo)
        return PromoBannerResponse.model_validate(promo)

    async def update_restaurant_promo(
        self,
        user: User,
        restaurant_id: int,
        promo_id: int,
        payload: MerchantPromoUpdate,
    ) -> PromoBannerResponse | None:
        await self._require_managed_restaurant(user, restaurant_id)
        promo = await self.repository.get_restaurant_promo(restaurant_id, promo_id)
        if promo is None:
            return None
        updated = await self.repository.update_restaurant_promo(promo, payload.model_dump(exclude_unset=True))
        await self.repository.save()
        await self.repository.refresh(updated)
        return PromoBannerResponse.model_validate(updated)

    async def delete_restaurant_promo(self, user: User, restaurant_id: int, promo_id: int) -> bool:
        await self._require_managed_restaurant(user, restaurant_id)
        promo = await self.repository.get_restaurant_promo(restaurant_id, promo_id)
        if promo is None:
            return False
        await self.repository.delete_restaurant_promo(promo)
        await self.repository.save()
        return True
