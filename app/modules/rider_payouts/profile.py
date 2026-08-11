from __future__ import annotations

from pydantic import BaseModel

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.rider_payouts.models import RiderPayout
from app.modules.rider_payouts.schemas import RiderPayoutResponse
from app.modules.rider_payouts.service import RiderPayoutService
from app.modules.rider_payouts.review import RiderReviewService
from app.modules.rider_payouts.tier import RIDER_TIERS, get_lifetime_delivery_count, tier_for_delivery_count
from app.modules.rider_payouts.wallet import WalletService


class RiderProfileResponse(BaseModel):
    riderUserId: int
    fullName: str
    riderWorkMode: str
    tier: str
    tierLabel: str
    lifetimeDeliveries: int
    deliveriesToNextTier: int | None = None
    nextTierLabel: str | None = None
    totalEarnings: float
    pendingEarnings: float
    paidEarnings: float
    walletBalance: float | None = None
    canAcceptOffers: bool = True
    averageRating: float | None = None
    totalReviews: int = 0
    recentDeliveries: list[RiderPayoutResponse] = []


class RiderProfileService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_profile(self, rider: User) -> RiderProfileResponse:
        lifetime_deliveries = await get_lifetime_delivery_count(self.session, rider.id)
        tier = tier_for_delivery_count(lifetime_deliveries)

        # Tiers are ordered highest -> lowest; find the next one above current.
        next_tier = None
        for candidate in reversed(RIDER_TIERS):
            if candidate.min_deliveries > tier.min_deliveries and lifetime_deliveries < candidate.min_deliveries:
                next_tier = candidate
                break
        deliveries_to_next = (next_tier.min_deliveries - lifetime_deliveries) if next_tier else None

        earnings_result = await self.session.execute(
            select(RiderPayout.status, func.coalesce(func.sum(RiderPayout.payout_amount), 0.0))
            .where(RiderPayout.rider_user_id == rider.id)
            .group_by(RiderPayout.status)
        )
        earnings_by_status = dict(earnings_result.all())
        pending_earnings = float(earnings_by_status.get("pending", 0.0))
        paid_earnings = float(earnings_by_status.get("paid", 0.0))

        wallet_balance: float | None = None
        can_accept_offers = True
        if rider.rider_work_mode == "platform":
            wallet_service = WalletService(self.session)
            wallet_balance = await wallet_service.get_balance(rider.id)
            can_accept_offers = await wallet_service.can_accept_offers(rider.id)

        recent = await RiderPayoutService(self.session).list_for_rider(rider.id)
        rating_summary = await RiderReviewService(self.session).get_rating_summary(rider.id)

        return RiderProfileResponse(
            riderUserId=rider.id,
            fullName=rider.full_name,
            riderWorkMode=rider.rider_work_mode,
            tier=tier.name,
            tierLabel=tier.label,
            lifetimeDeliveries=lifetime_deliveries,
            deliveriesToNextTier=deliveries_to_next,
            nextTierLabel=next_tier.label if next_tier else None,
            totalEarnings=round(pending_earnings + paid_earnings, 2),
            pendingEarnings=round(pending_earnings, 2),
            paidEarnings=round(paid_earnings, 2),
            walletBalance=wallet_balance,
            canAcceptOffers=can_accept_offers,
            averageRating=rating_summary.averageRating,
            totalReviews=rating_summary.totalReviews,
            recentDeliveries=recent[:20],
        )
