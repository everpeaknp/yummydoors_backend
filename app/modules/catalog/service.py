from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import MenuItemResponse, MenuItemSummary
from app.modules.catalog.models import MenuItem

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
