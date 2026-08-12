from __future__ import annotations

from pydantic import BaseModel

from app.modules.auth.models import User
from app.modules.rider_payouts.review import RiderReviewService
from app.modules.rider_payouts.tier import get_lifetime_delivery_count
from app.modules.rider_payroll.service import RiderPayrollService
from sqlalchemy.ext.asyncio import AsyncSession


class RiderProfileResponse(BaseModel):
    riderUserId: int
    fullName: str
    riderWorkMode: str
    lifetimeDeliveries: int
    averageRating: float | None = None
    totalReviews: int = 0
    monthlySalary: float | None = None
    currentPeriod: str
    currentPeriodStatus: str | None = None
    lastPaidAt: str | None = None


class RiderProfileService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_profile(self, rider: User) -> RiderProfileResponse:
        lifetime_deliveries = await get_lifetime_delivery_count(self.session, rider.id)
        rating_summary = await RiderReviewService(self.session).get_rating_summary(rider.id)
        payroll_status = await RiderPayrollService(self.session).get_my_status(rider.id)

        return RiderProfileResponse(
            riderUserId=rider.id,
            fullName=rider.full_name,
            riderWorkMode=rider.rider_work_mode,
            lifetimeDeliveries=lifetime_deliveries,
            averageRating=rating_summary.averageRating,
            totalReviews=rating_summary.totalReviews,
            monthlySalary=payroll_status.monthlyAmount,
            currentPeriod=payroll_status.currentPeriod,
            currentPeriodStatus=payroll_status.currentPeriodStatus,
            lastPaidAt=payroll_status.lastPaidAt.isoformat() if payroll_status.lastPaidAt else None,
        )
