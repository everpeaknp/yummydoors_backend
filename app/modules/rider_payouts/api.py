from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.rider_payouts.schemas import RiderPayoutResponse
from app.modules.rider_payouts.service import RiderPayoutService

router = APIRouter(tags=["Rider Payouts"])


@router.get("/riders/me/payouts", response_model=List[RiderPayoutResponse])
async def list_my_payouts(
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = RiderPayoutService(db)
    return await service.list_for_rider(current_user.id)


@router.get(
    "/admin/rider-payouts",
    response_model=List[RiderPayoutResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_admin_payouts(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = RiderPayoutService(db)
    return await service.list_all(status_filter=status_filter)


@router.post(
    "/admin/rider-payouts/{payout_id}/mark-paid",
    response_model=RiderPayoutResponse,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def mark_payout_paid(
    payout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderPayoutService(db)
    return await service.mark_paid(payout_id=payout_id, admin_user_id=current_user.id)
