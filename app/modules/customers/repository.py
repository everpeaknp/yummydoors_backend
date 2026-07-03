from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.customers.models import CustomerAddress
from app.modules.auth.models import User


class CustomerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_profile(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.addresses))
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_user_profile(self, user_id: int, update_data: dict) -> User | None:
        user = await self.get_user_profile(user_id)
        if not user:
            return None
        
        for key, value in update_data.items():
            setattr(user, key, value)
            
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_user_by_phone(self, phone: str) -> User | None:
        stmt = select(User).where(User.phone == phone)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_address(self, user_id: int, address_data: dict) -> CustomerAddress:
        address = CustomerAddress(user_id=user_id, **address_data)
        self.session.add(address)
        await self.session.commit()
        await self.session.refresh(address)
        return address

    async def get_address(self, address_id: int, user_id: int) -> CustomerAddress | None:
        stmt = select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.user_id == user_id,
            CustomerAddress.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_addresses(self, user_id: int) -> Sequence[CustomerAddress]:
        stmt = select(CustomerAddress).where(
            CustomerAddress.user_id == user_id,
            CustomerAddress.is_active == True
        ).order_by(CustomerAddress.id.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_address(self, address_id: int, user_id: int, update_data: dict) -> CustomerAddress | None:
        address = await self.get_address(address_id, user_id)
        if not address:
            return None
            
        for key, value in update_data.items():
            setattr(address, key, value)
            
        self.session.add(address)
        await self.session.commit()
        await self.session.refresh(address)
        return address

    async def delete_address(self, address_id: int, user_id: int) -> bool:
        address = await self.get_address(address_id, user_id)
        if not address:
            return False
            
        address.is_active = False
        self.session.add(address)
        
        # If this was the default address, clear it
        user = await self.get_user_profile(user_id)
        if user and user.default_address_id == address_id:
            user.default_address_id = None
            self.session.add(user)
            
        await self.session.commit()
        return True
