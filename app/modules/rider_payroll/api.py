from typing import List

from fastapi import APIRouter, Depends

from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.rider_payroll.schemas import (
    MyPayrollStatusResponse,
    RiderPayrollPaymentResponse,
    RiderSalaryResponse,
    SetRiderSalaryRequest,
)
from app.modules.rider_payroll.service import RiderPayrollService, current_period

router = APIRouter(tags=["Rider Payroll"])


@router.get("/riders/me/payroll", response_model=MyPayrollStatusResponse)
async def get_my_payroll_status(
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    return await RiderPayrollService(db).get_my_status(current_user.id)


@router.patch(
    "/admin/riders/{rider_user_id}/salary",
    response_model=RiderSalaryResponse,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def set_rider_salary(
    rider_user_id: int,
    payload: SetRiderSalaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RiderPayrollService(db).set_salary(
        rider_user_id=rider_user_id, monthly_amount=payload.monthlyAmount, admin_user_id=current_user.id
    )


@router.get(
    "/admin/rider-salaries",
    response_model=List[RiderSalaryResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_rider_salaries(db: AsyncSession = Depends(get_db)):
    return await RiderPayrollService(db).list_salaries()


@router.get(
    "/admin/rider-payroll",
    response_model=List[RiderPayrollPaymentResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_rider_payroll(period: str | None = None, db: AsyncSession = Depends(get_db)):
    return await RiderPayrollService(db).list_payroll_for_period(period or current_period())


@router.post(
    "/admin/rider-payroll/{payment_id}/mark-paid",
    response_model=RiderPayrollPaymentResponse,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def mark_rider_payroll_paid(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RiderPayrollService(db).mark_paid(payment_id=payment_id, admin_user_id=current_user.id)
