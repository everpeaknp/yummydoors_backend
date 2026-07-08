import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import AsyncSessionLocal
from app.modules.auth.models import User
from app.core.security import create_access_token

client = TestClient(app)

async def test_endpoint():
    async with AsyncSessionLocal() as db:
        user = User(email="test2@example.com", full_name="Test", hashed_password="dummy", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        token = create_access_token(user.id)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/favorites/menu-items/1", headers=headers)
    print("STATUS:", response.status_code)
    print("RESPONSE:", response.json())

if __name__ == "__main__":
    asyncio.run(test_endpoint())
