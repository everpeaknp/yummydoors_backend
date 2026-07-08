import asyncio
import json
from app.db.session import AsyncSessionLocal
from app.modules.favorites.repository import FavoritesRepository
from app.modules.favorites.schemas import FavoriteMenuItemResponse
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.restaurants.api import build_restaurant_summary_with_context
from app.modules.auth.models import User
from app.modules.restaurants.models import Restaurant, RestaurantCategory
from app.modules.catalog.models import MenuItem

async def test_add_favorite():
    async with AsyncSessionLocal() as db:
        repo = FavoritesRepository(db)
        
        # get menu item 2
        menu_item = await repo.get_menu_item(2)
        if not menu_item:
            print("Menu item 2 not found.")
            return

        try:
            # test serialization
            existing = await repo.get_menu_item_favorite(1, 2)
            favorite = existing or await repo.add_menu_item_favorite(1, 2)
            if existing is not None:
                await repo.db.refresh(existing)
                
            print("Favorite ID:", favorite.id)
            print("Created At:", favorite.created_at)
            
            data = FavoriteMenuItemResponse(
                id=favorite.id,
                created_at=favorite.created_at.isoformat() if favorite.created_at else None,
                menu_item=MenuItemSummary.model_validate(menu_item),
                restaurant=build_restaurant_summary_with_context(
                    restaurant=menu_item.restaurant,
                    latitude=None,
                    longitude=None,
                ),
            )
            print("Serialization successful:", data.id)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_add_favorite())
