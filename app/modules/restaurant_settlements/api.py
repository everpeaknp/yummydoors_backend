from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.restaurant_settlements.schemas import RestaurantSettlementResponse
from app.modules.restaurant_settlements.service import RestaurantSettlementService

router = APIRouter(tags=["Restaurant Settlements"])


@router.get(
    "/admin/restaurant-settlements",
    response_model=List[RestaurantSettlementResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_admin_settlements(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = RestaurantSettlementService(db)
    return await service.list_all(status_filter=status_filter)


@router.post(
    "/admin/restaurant-settlements/{settlement_id}/mark-settled",
    response_model=RestaurantSettlementResponse,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def mark_settlement_settled(
    settlement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RestaurantSettlementService(db)
    return await service.mark_settled(settlement_id=settlement_id, admin_user_id=current_user.id)
