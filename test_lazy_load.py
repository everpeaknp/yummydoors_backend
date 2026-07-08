import asyncio
from app.db.session import AsyncSessionLocal
from app.modules.favorites.repository import FavoritesRepository
from app.modules.catalog.repository import CatalogRepository

async def test_lazy_load():
    async with AsyncSessionLocal() as db:
        repo = FavoritesRepository(db)
        menu_item = await repo.get_menu_item(1)
        if not menu_item:
            print("Menu item not found.")
            return
        
        try:
            print("Menu Item:", menu_item.name)
            print("Restaurant:", menu_item.restaurant.name)
            print("Category Links Count:", len(menu_item.restaurant.category_links))
            if menu_item.restaurant.category_links:
                print("First Category:", menu_item.restaurant.category_links[0].category.name)
        except Exception as e:
            print("ERROR ACCESING RELATIONSHIP:", e)

if __name__ == "__main__":
    asyncio.run(test_lazy_load())
