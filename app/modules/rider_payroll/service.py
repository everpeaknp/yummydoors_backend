from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import User
from app.modules.rider_payroll.models import RiderPayrollPayment, RiderSalary
from app.modules.rider_payroll.schemas import (
    MyPayrollStatusResponse,
    RiderPayrollPaymentResponse,
    RiderSalaryResponse,
)


def current_period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


class RiderPayrollService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_salary(self, *, rider_user_id: int, monthly_amount: float, admin_user_id: int) -> RiderSalaryResponse:
        rider = await self.session.get(User, rider_user_id)
        if rider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found.")
        if rider.rider_work_mode != "platform":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only platform-tier riders are salaried. Grant platform status first.",
            )

        salary = await self.session.scalar(select(RiderSalary).where(RiderSalary.rider_user_id == rider_user_id))
        if salary is None:
            salary = RiderSalary(rider_user_id=rider_user_id, monthly_amount=monthly_amount, set_by_user_id=admin_user_id)
            self.session.add(salary)
        else:
            salary.monthly_amount = monthly_amount
            salary.set_by_user_id = admin_user_id
        await self.session.commit()
        await self.session.refresh(salary)
        return RiderSalaryResponse(
            riderUserId=rider.id, riderName=rider.full_name, monthlyAmount=salary.monthly_amount, updatedAt=salary.updated_at
        )

    async def list_salaries(self) -> list[RiderSalaryResponse]:
        stmt = select(RiderSalary).options(selectinload(RiderSalary.rider)).order_by(RiderSalary.updated_at.desc())
        result = await self.session.execute(stmt)
        return [
            RiderSalaryResponse(
                riderUserId=row.rider_user_id,
                riderName=row.rider.full_name if row.rider else "Rider",
                monthlyAmount=row.monthly_amount,
                updatedAt=row.updated_at,
            )
            for row in result.scalars().all()
        ]

    async def list_payroll_for_period(self, period: str) -> list[RiderPayrollPaymentResponse]:
        """Get-or-create a pending payroll row (snapshotting the rider's
        current salary) for every salaried rider for the given period, then
        return the full list -- so the admin screen always has an
        actionable row for the current period without a separate cron job
        needing to pre-create them."""
        salaries = await self.session.execute(select(RiderSalary))
        salary_rows = list(salaries.scalars().all())

        existing = await self.session.execute(
            select(RiderPayrollPayment).where(RiderPayrollPayment.period == period)
        )
        existing_rider_ids = {row.rider_user_id for row in existing.scalars().all()}

        for salary in salary_rows:
            if salary.rider_user_id in existing_rider_ids:
                continue
            self.session.add(
                RiderPayrollPayment(
                    rider_user_id=salary.rider_user_id,
                    period=period,
                    amount=salary.monthly_amount,
                    status="pending",
                )
            )
        if len(existing_rider_ids) < len(salary_rows):
            await self.session.commit()

        stmt = (
            select(RiderPayrollPayment)
            .options(selectinload(RiderPayrollPayment.rider))
            .where(RiderPayrollPayment.period == period)
            .order_by(RiderPayrollPayment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_response(row) for row in result.scalars().all()]

    async def mark_paid(self, *, payment_id: int, admin_user_id: int) -> RiderPayrollPaymentResponse:
        payment = await self.session.get(RiderPayrollPayment, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll record not found.")
        if payment.status != "paid":
            payment.status = "paid"
            payment.paid_at = datetime.now(UTC)
            payment.paid_by_user_id = admin_user_id
            await self.session.commit()

        refreshed = await self.session.execute(
            select(RiderPayrollPayment).options(selectinload(RiderPayrollPayment.rider)).where(RiderPayrollPayment.id == payment_id)
        )
        return self._to_response(refreshed.scalar_one())

    async def get_my_status(self, rider_user_id: int) -> MyPayrollStatusResponse:
        salary = await self.session.scalar(select(RiderSalary).where(RiderSalary.rider_user_id == rider_user_id))
        period = current_period()
        current_row = await self.session.scalar(
            select(RiderPayrollPayment).where(
                RiderPayrollPayment.rider_user_id == rider_user_id, RiderPayrollPayment.period == period
            )
        )
        last_paid = await self.session.scalar(
            select(RiderPayrollPayment)
            .where(RiderPayrollPayment.rider_user_id == rider_user_id, RiderPayrollPayment.status == "paid")
            .order_by(RiderPayrollPayment.paid_at.desc())
        )
        return MyPayrollStatusResponse(
            monthlyAmount=salary.monthly_amount if salary else None,
            currentPeriod=period,
            currentPeriodStatus=current_row.status if current_row else None,
            lastPaidAt=last_paid.paid_at if last_paid else None,
        )

    @staticmethod
    def _to_response(row: RiderPayrollPayment) -> RiderPayrollPaymentResponse:
        return RiderPayrollPaymentResponse(
            id=row.id,
            riderUserId=row.rider_user_id,
            riderName=row.rider.full_name if row.rider else "Rider",
            period=row.period,
            amount=row.amount,
            status=row.status,
            paidAt=row.paid_at,
            createdAt=row.created_at,
        )
