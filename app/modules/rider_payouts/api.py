from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import require_role
from app.modules.auth.models import User
from app.modules.rider_payouts.profile import RiderProfileResponse, RiderProfileService

router = APIRouter(tags=["Rider Payouts"])


@router.get("/riders/me/profile", response_model=RiderProfileResponse)
async def get_my_rider_profile(
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = RiderProfileService(db)
    return await service.get_profile(current_user)
