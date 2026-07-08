import asyncio
from app.db.session import AsyncSessionLocal
from app.modules.favorites.repository import FavoritesRepository
from app.modules.favorites.schemas import FavoriteMenuItemResponse
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.restaurants.api import build_restaurant_summary_with_context

async def run():
    async with AsyncSessionLocal() as db:
        repo = FavoritesRepository(db)
        from sqlalchemy import select
        from app.modules.catalog.models import MenuItem
        stmt = select(MenuItem).limit(1)
        res = await repo.db.execute(stmt)
        first_item = res.scalars().first()
        if not first_item:
            print("Database is completely empty.")
            return
            
        menu_item = await repo.get_menu_item(first_item.id)

        print("Testing serialization...")
        try:
            summary = MenuItemSummary.model_validate(menu_item)
            print("MenuItemSummary OK")
            
            rest = build_restaurant_summary_with_context(
                restaurant=menu_item.restaurant,
                latitude=None,
                longitude=None,
            )
            print("RestaurantCardSummary OK")
            
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
