import asyncio
import logging
from sqlalchemy import select
import app.db.base  # This registers all models with SQLAlchemy
from app.db.session import AsyncSessionLocal
from app.modules.auth.models import User
from app.modules.customers.models import CustomerAddress
from app.modules.restaurants.models import Category, Restaurant, RestaurantCategory
from app.modules.catalog.models import MenuItem, FoodType, MenuModifierGroup, MenuModifierItem
from app.modules.merchandising.models import PromoBanner, PromoPlacement, PromoTargetType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    async with AsyncSessionLocal() as db:
        logger.info("Starting database seed...")
        
        # 1. Create a User (Customer)
        user = User(email="seed_test@example.com", password_hash="hashed", full_name="Test Customer")
        db.add(user)
        await db.flush()
        
        # 2. Create an Address
        address = CustomerAddress(
            user_id=user.id,
            label="Home",
            recipient_name="Test Customer",
            phone_country_code="+977",
            phone_number="9800000000",
            address_line_1="Ratnachowk",
            address_line_2="Street No 14",
            city="Pokhara",
            latitude=28.2096,
            longitude=83.9856,
            is_active=True
        )
        db.add(address)
        await db.flush()
        user.default_address_id = address.id
        
        # 3. Create or Fetch Categories
        pizza_cat = (await db.execute(select(Category).where(Category.slug=="pizza"))).scalars().first()
        if not pizza_cat:
            pizza_cat = Category(slug="pizza", name="Pizza", icon_url="https://example.com/pizza.png", sort_order=1, is_featured=True)
            db.add(pizza_cat)
            
        burger_cat = (await db.execute(select(Category).where(Category.slug=="burger"))).scalars().first()
        if not burger_cat:
            burger_cat = Category(slug="burger", name="Burger", icon_url="https://example.com/burger.png", sort_order=2, is_featured=True)
            db.add(burger_cat)
        
        await db.flush()
        
        # 4. Create or Fetch Restaurants
        rest1 = (await db.execute(select(Restaurant).where(Restaurant.slug=="mario-pizza"))).scalars().first()
        if not rest1:
            rest1 = Restaurant(
                slug="mario-pizza", name="Mario's Pizza", cover_image_url="https://example.com/rest1_cover.jpg",
                logo_url="https://example.com/rest1_logo.jpg", short_description="Best wood-fired pizza in town",
                primary_cuisine_label="Italian", city="Pokhara", rating_average=4.5, review_count=120,
                has_free_delivery=True, is_featured=True
            )
            db.add(rest1)
            
        rest2 = (await db.execute(select(Restaurant).where(Restaurant.slug=="burger-hub"))).scalars().first()
        if not rest2:
            rest2 = Restaurant(
                slug="burger-hub", name="The Burger Hub", cover_image_url="https://example.com/rest2_cover.jpg",
                logo_url="https://example.com/rest2_logo.jpg", short_description="Juicy smash burgers",
                primary_cuisine_label="American", city="Pokhara", rating_average=4.2, review_count=85,
                is_featured=False
            )
            db.add(rest2)
            
        await db.flush()
        
        # Link categories safely
        rc1 = (await db.execute(select(RestaurantCategory).where(RestaurantCategory.restaurant_id==rest1.id, RestaurantCategory.category_id==pizza_cat.id))).scalars().first()
        if not rc1:
            db.add(RestaurantCategory(restaurant_id=rest1.id, category_id=pizza_cat.id))
            
        rc2 = (await db.execute(select(RestaurantCategory).where(RestaurantCategory.restaurant_id==rest2.id, RestaurantCategory.category_id==burger_cat.id))).scalars().first()
        if not rc2:
            db.add(RestaurantCategory(restaurant_id=rest2.id, category_id=burger_cat.id))
        await db.flush()
        
        # 5. Create or Fetch Menu Items
        item1 = (await db.execute(select(MenuItem).where(MenuItem.slug=="margherita-pizza"))).scalars().first()
        if not item1:
            item1 = MenuItem(
                restaurant_id=rest1.id, category_id=pizza_cat.id, slug="margherita-pizza", name="Margherita Pizza",
                description="Classic tomato sauce and mozzarella", price=450.0, food_type=FoodType.veg,
                is_featured=True, popularity_score=100
            )
            db.add(item1)
            
        item2 = (await db.execute(select(MenuItem).where(MenuItem.slug=="classic-cheeseburger"))).scalars().first()
        if not item2:
            item2 = MenuItem(
                restaurant_id=rest2.id, category_id=burger_cat.id, slug="classic-cheeseburger", name="Classic Cheeseburger",
                description="Beef patty with cheddar", price=350.0, food_type=FoodType.non_veg,
                is_popular=True, popularity_score=90
            )
            db.add(item2)
        await db.flush()
        
        # Add modifier to Pizza
        size_group = MenuModifierGroup(menu_item_id=item1.id, name="Size", is_required=True, min_selections=1, max_selections=1)
        db.add(size_group)
        await db.flush()
        db.add(MenuModifierItem(group_id=size_group.id, name="Small", price_adjustment=0.0))
        db.add(MenuModifierItem(group_id=size_group.id, name="Large", price_adjustment=200.0))
        
        # 6. Create Promos
        promo1 = PromoBanner(
            title="50% Off Pizza",
            image_url="https://example.com/promo1.jpg",
            placement=PromoPlacement.home_carousel,
            target_type=PromoTargetType.restaurant,
            target_id=rest1.id,
            cta_text="Order Now"
        )
        db.add(promo1)
        
        await db.commit()
        logger.info("Seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
