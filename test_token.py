import asyncio
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.core.security import create_access_token

async def get_token():
    async with SessionLocal() as db:
        user = User(email="test_user@example.com", full_name="Test", hashed_password="dummy", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(create_access_token(user.id))

if __name__ == "__main__":
    asyncio.run(get_token())
