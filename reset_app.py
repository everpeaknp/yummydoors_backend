import asyncio
from sqlalchemy import update
from app.db.session import AsyncSessionLocal
from app.modules.workspaces.models import MerchantApplication, Workspace, MerchantRestaurantRequest

async def main():
    async with AsyncSessionLocal() as session:
        # Reset everything to draft so the user can test the UI again
        await session.execute(update(MerchantApplication).values(status='draft'))
        await session.execute(update(MerchantRestaurantRequest).values(status='draft'))
        await session.execute(update(Workspace).values(status='active'))
        await session.commit()
        print("Successfully reset to draft!")

if __name__ == "__main__":
    asyncio.run(main())
