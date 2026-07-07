from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.orders.schemas import OrderResponse, CheckoutRequest, OrderSummaryRequest, OrderSummaryResponse
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/summary", response_model=OrderSummaryResponse)
async def get_order_summary(
    summary_request: OrderSummaryRequest,
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    return await service.calculate_summary(summary_request)

@router.get("", response_model=List[OrderResponse])
async def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    return await service.get_my_orders(current_user.id)

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    return await service.get_order(current_user.id, order_id)

@router.post("/checkout/{cart_id}", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def checkout_cart(
    cart_id: int,
    checkout_data: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    return await service.checkout_cart(current_user.id, cart_id, checkout_data)
