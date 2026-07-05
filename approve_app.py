import asyncio
from app.db.base import Base # This imports all models
from app.db.session import AsyncSessionLocal
from app.modules.workspaces.service import WorkspaceService

async def main():
    async with AsyncSessionLocal() as session:
        service = WorkspaceService(session)
        apps = await service.repository.list_all_applications()
        for app in apps:
            if app.status == "submitted":
                try:
                    await service.approve_application(application_id=app.id, admin_notes="Auto-approved for testing.")
                    print(f"Successfully approved application {app.id}!")
                except Exception as e:
                    print(f"Error approving {app.id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
