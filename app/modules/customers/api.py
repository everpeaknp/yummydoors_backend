from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.customers.schemas import (
    CustomerAddressCreate,
    CustomerAddressUpdate,
    CustomerAddressResponse,
    CustomerProfileResponse,
    CustomerProfileUpdate
)
from app.modules.customers.service import CustomerService

router = APIRouter(prefix="/me", tags=["Customers"])


@router.get("/profile", response_model=CustomerProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CustomerService(db)
    return await service.get_profile(current_user.id)


@router.patch("/profile", response_model=CustomerProfileResponse)
async def update_my_profile(
    update_data: CustomerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CustomerService(db)
    return await service.update_profile(current_user.id, update_data)


@router.get("/addresses", response_model=List[CustomerAddressResponse])
async def list_my_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CustomerService(db)
    return await service.list_addresses(current_user.id)


@router.post("/addresses", response_model=CustomerAddressResponse, status_code=status.HTTP_201_CREATED)
async def create_my_address(
    address_data: CustomerAddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CustomerService(db)
    return await service.create_address(current_user.id, address_data)


@router.patch("/addresses/{address_id}", response_model=CustomerAddressResponse)
async def update_my_address(
    address_id: int,
    update_data: CustomerAddressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CustomerService(db)
    return await service.update_address(current_user.id, address_id, update_data)


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CustomerService(db)
    await service.delete_address(current_user.id, address_id)


@router.post("/addresses/{address_id}/default", status_code=status.HTTP_204_NO_CONTENT)
async def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CustomerService(db)
    await service.set_default_address(current_user.id, address_id)
