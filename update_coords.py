import asyncio
from sqlalchemy import update
import app.db.base
from app.db.session import AsyncSessionLocal
from app.modules.restaurants.models import Restaurant

async def main():
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Restaurant)
            .where(Restaurant.slug == 'mario-pizza')
            .values(latitude=28.2100, longitude=83.9860)
        )
        await session.execute(
            update(Restaurant)
            .where(Restaurant.slug == 'burger-hub')
            .values(latitude=28.2080, longitude=83.9850)
        )
        await session.commit()
        print("Updated restaurant coordinates!")

if __name__ == "__main__":
    asyncio.run(main())
