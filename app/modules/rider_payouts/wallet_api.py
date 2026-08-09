from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.rider_payouts.wallet import WalletService
from app.modules.rider_payouts.wallet_schemas import (
    AdminWalletAdjustRequest,
    RiderWalletResponse,
    RiderWalletTransactionResponse,
)

router = APIRouter(tags=["Rider Wallet"])


@router.get("/riders/me/wallet", response_model=RiderWalletResponse)
async def get_my_wallet(
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    return await service.get_wallet_response(current_user.id)


@router.get("/riders/me/wallet/transactions", response_model=List[RiderWalletTransactionResponse])
async def list_my_wallet_transactions(
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = WalletService(db)
    return await service.list_transactions(current_user.id)


@router.get(
    "/admin/rider-wallets",
    response_model=List[RiderWalletResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_admin_rider_wallets(db: AsyncSession = Depends(get_db)):
    service = WalletService(db)
    return await service.list_all_wallets()


@router.get(
    "/admin/rider-wallets/{rider_user_id}",
    response_model=RiderWalletResponse,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def get_admin_rider_wallet(rider_user_id: int, db: AsyncSession = Depends(get_db)):
    service = WalletService(db)
    return await service.get_wallet_response(rider_user_id)


@router.get(
    "/admin/rider-wallets/{rider_user_id}/transactions",
    response_model=List[RiderWalletTransactionResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_admin_rider_wallet_transactions(rider_user_id: int, db: AsyncSession = Depends(get_db)):
    service = WalletService(db)
    return await service.list_transactions(rider_user_id)


@router.post(
    "/admin/rider-wallets/{rider_user_id}/adjust",
    response_model=RiderWalletResponse,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def adjust_rider_wallet(
    rider_user_id: int,
    payload: AdminWalletAdjustRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Positive amount credits the wallet (rider topped up), negative
    debits it (correcting a mistaken credit, manual recovery, etc — the
    schema already requires a note for the negative case)."""
    service = WalletService(db)
    return await service.admin_adjust(
        rider_user_id=rider_user_id, amount=payload.amount, admin_user_id=current_user.id, note=payload.note
    )
