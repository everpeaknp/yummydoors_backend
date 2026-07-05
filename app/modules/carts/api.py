from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.carts.schemas import (
    CartContextUpdate,
    CartCouponApplyRequest,
    CartItemCreate,
    CartItemUpdate,
    CartResponse,
)
from app.modules.carts.service import CartService

router = APIRouter(prefix="/carts", tags=["Carts"])

@router.get("", response_model=List[CartResponse])
async def list_my_carts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CartService(db)
    return await service.get_all_active_carts(current_user.id)

@router.get("/{restaurant_id}", response_model=CartResponse)
async def get_cart(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CartService(db)
    return await service.get_active_cart(current_user.id, restaurant_id)

@router.post("/{restaurant_id}/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    restaurant_id: int,
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CartService(db)
    return await service.add_item_to_cart(current_user.id, restaurant_id, item_data)

@router.patch("/{restaurant_id}/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    restaurant_id: int,
    item_id: int,
    update_data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CartService(db)
    return await service.update_item_quantity(current_user.id, restaurant_id, item_id, update_data)

@router.patch("/{restaurant_id}/context", response_model=CartResponse)
async def update_cart_context(
    restaurant_id: int,
    payload: CartContextUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CartService(db)
    return await service.update_cart_context(current_user.id, restaurant_id, payload)

@router.post("/{restaurant_id}/coupon", response_model=CartResponse)
async def apply_coupon(
    restaurant_id: int,
    payload: CartCouponApplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CartService(db)
    return await service.apply_coupon(current_user.id, restaurant_id, payload)

@router.delete("/{restaurant_id}/coupon", response_model=CartResponse)
async def remove_coupon(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CartService(db)
    return await service.remove_coupon(current_user.id, restaurant_id)

@router.delete("/{restaurant_id}/items/{item_id}", response_model=CartResponse)
async def remove_cart_item(
    restaurant_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CartService(db)
    return await service.remove_item_from_cart(current_user.id, restaurant_id, item_id)
