import asyncio
from app.db.session import AsyncSessionLocal
from app.modules.favorites.repository import FavoritesRepository
from app.modules.favorites.schemas import FavoriteMenuItemResponse
from app.modules.catalog.schemas import MenuItemSummary
from app.modules.restaurants.api import build_restaurant_summary_with_context
from app.modules.auth.models import User

async def test_logic():
    async with AsyncSessionLocal() as db:
        user = User(email="test3@example.com", full_name="Test", hashed_password="dummy", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        repo = FavoritesRepository(db)
        menu_item = await repo.get_menu_item(1)
        if not menu_item:
            print("Menu item not found.")
            return

        # SIMULATE POST REQUEST 1 (should insert)
        print("POST 1")
        existing = await repo.get_menu_item_favorite(user.id, 1)
        favorite = existing or await repo.add_menu_item_favorite(user.id, 1)
        if existing is not None:
            await repo.db.refresh(existing)
            
        data = FavoriteMenuItemResponse(
            id=favorite.id,
            created_at=favorite.created_at.isoformat() if favorite.created_at else "",
            menu_item=MenuItemSummary.model_validate(menu_item),
            restaurant=build_restaurant_summary_with_context(
                restaurant=menu_item.restaurant,
                latitude=None,
                longitude=None,
            ),
        )
        print("POST 1 success:", data.id)

        # SIMULATE POST REQUEST 2 (already exists)
        print("POST 2")
        existing2 = await repo.get_menu_item_favorite(user.id, 1)
        favorite2 = existing2 or await repo.add_menu_item_favorite(user.id, 1)
        if existing2 is not None:
            await repo.db.refresh(existing2)
            
        data2 = FavoriteMenuItemResponse(
            id=favorite2.id,
            created_at=favorite2.created_at.isoformat() if favorite2.created_at else "",
            menu_item=MenuItemSummary.model_validate(menu_item),
            restaurant=build_restaurant_summary_with_context(
                restaurant=menu_item.restaurant,
                latitude=None,
                longitude=None,
            ),
        )
        print("POST 2 success:", data2.id)

if __name__ == "__main__":
    asyncio.run(test_logic())
