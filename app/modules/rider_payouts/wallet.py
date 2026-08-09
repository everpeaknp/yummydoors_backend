from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.rider_payouts.wallet_models import RiderWallet, RiderWalletTransaction
from app.modules.rider_payouts.wallet_schemas import RiderWalletResponse, RiderWalletTransactionResponse


class WalletService:
    """Freelance/platform riders pre-fund a wallet (topped up manually —
    rider pays via WhatsApp, admin credits it) the same way inDrive drivers
    do in cash-heavy markets. For a COD delivery the rider already has the
    customer's cash in hand, so the platform can't collect its commission
    any other way — it debits the wallet instead. If the balance drops to
    zero or below, the rider stops receiving new offers until they top up.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_wallet(self, rider_user_id: int) -> RiderWallet:
        wallet = await self.session.scalar(
            select(RiderWallet).where(RiderWallet.rider_user_id == rider_user_id)
        )
        if wallet is not None:
            return wallet
        wallet = RiderWallet(rider_user_id=rider_user_id, balance=0.0)
        self.session.add(wallet)
        await self.session.commit()
        await self.session.refresh(wallet)
        return wallet

    async def get_balance(self, rider_user_id: int) -> float:
        wallet = await self.session.scalar(
            select(RiderWallet).where(RiderWallet.rider_user_id == rider_user_id)
        )
        return wallet.balance if wallet is not None else 0.0

    async def can_accept_offers(self, rider_user_id: int) -> bool:
        """Riders who've never had a wallet row (private/platform riders,
        or a freelancer who's never had a COD delivery yet) are not gated —
        only an actual negative/zero balance blocks new offers."""
        wallet = await self.session.scalar(
            select(RiderWallet).where(RiderWallet.rider_user_id == rider_user_id)
        )
        if wallet is None:
            return True
        return wallet.balance > 0

    async def debit_commission(
        self, *, rider_user_id: int, amount: float, order_id: int | None, note: str | None = None
    ) -> RiderWallet:
        wallet = await self.get_or_create_wallet(rider_user_id)
        wallet.balance = round(wallet.balance - amount, 2)
        self.session.add(
            RiderWalletTransaction(
                wallet_id=wallet.id,
                order_id=order_id,
                kind="debit",
                amount=amount,
                balance_after=wallet.balance,
                note=note,
            )
        )
        await self.session.commit()
        await self.session.refresh(wallet)
        return wallet

    async def credit_top_up(
        self, *, rider_user_id: int, amount: float, admin_user_id: int, note: str | None = None
    ) -> RiderWallet:
        wallet = await self.get_or_create_wallet(rider_user_id)
        wallet.balance = round(wallet.balance + amount, 2)
        self.session.add(
            RiderWalletTransaction(
                wallet_id=wallet.id,
                order_id=None,
                kind="credit",
                amount=amount,
                balance_after=wallet.balance,
                note=note,
                created_by_user_id=admin_user_id,
            )
        )
        await self.session.commit()
        await self.session.refresh(wallet)
        return wallet

    async def get_wallet_response(self, rider_user_id: int) -> RiderWalletResponse:
        wallet = await self.session.scalar(
            select(RiderWallet)
            .options(selectinload(RiderWallet.rider))
            .where(RiderWallet.rider_user_id == rider_user_id)
        )
        balance = wallet.balance if wallet is not None else 0.0
        return RiderWalletResponse(
            riderUserId=rider_user_id,
            riderName=wallet.rider.full_name if wallet is not None and wallet.rider else None,
            balance=balance,
            canAcceptOffers=balance > 0 if wallet is not None else True,
        )

    async def list_transactions(self, rider_user_id: int) -> list[RiderWalletTransactionResponse]:
        wallet = await self.session.scalar(
            select(RiderWallet).where(RiderWallet.rider_user_id == rider_user_id)
        )
        if wallet is None:
            return []
        result = await self.session.execute(
            select(RiderWalletTransaction)
            .where(RiderWalletTransaction.wallet_id == wallet.id)
            .order_by(RiderWalletTransaction.created_at.desc())
        )
        return [
            RiderWalletTransactionResponse(
                id=t.id,
                kind=t.kind,
                amount=t.amount,
                balanceAfter=t.balance_after,
                note=t.note,
                orderId=t.order_id,
                createdAt=t.created_at,
            )
            for t in result.scalars().all()
        ]

    async def list_all_wallets(self) -> list[RiderWalletResponse]:
        result = await self.session.execute(
            select(RiderWallet).options(selectinload(RiderWallet.rider)).order_by(RiderWallet.balance.asc())
        )
        return [
            RiderWalletResponse(
                riderUserId=w.rider_user_id,
                riderName=w.rider.full_name if w.rider else None,
                balance=w.balance,
                canAcceptOffers=w.balance > 0,
            )
            for w in result.scalars().all()
        ]

    async def admin_top_up(self, *, rider_user_id: int, amount: float, admin_user_id: int, note: str | None) -> RiderWalletResponse:
        await self.credit_top_up(rider_user_id=rider_user_id, amount=amount, admin_user_id=admin_user_id, note=note)
        return await self.get_wallet_response(rider_user_id)
