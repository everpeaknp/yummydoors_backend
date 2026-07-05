from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.modules.carts.models import Cart, CartItem, CartStatus
from app.modules.catalog.models import MenuItem
from app.modules.customers.models import CustomerAddress

class CartRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_cart(self, customer_id: int, restaurant_id: int) -> Optional[Cart]:
        stmt = select(Cart).options(
            selectinload(Cart.items).selectinload(CartItem.menu_item),
            selectinload(Cart.restaurant),
            selectinload(Cart.address),
        ).where(
            and_(
                Cart.customer_id == customer_id,
                Cart.restaurant_id == restaurant_id,
                Cart.status == CartStatus.active
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_active_carts(self, customer_id: int) -> List[Cart]:
        stmt = select(Cart).options(
            selectinload(Cart.items).selectinload(CartItem.menu_item),
            selectinload(Cart.restaurant),
            selectinload(Cart.address),
        ).where(
            and_(
                Cart.customer_id == customer_id,
                Cart.status == CartStatus.active
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_cart(self, customer_id: int, restaurant_id: int) -> Cart:
        cart = Cart(customer_id=customer_id, restaurant_id=restaurant_id)
        self.session.add(cart)
        await self.session.commit()
        await self.session.refresh(cart)
        return cart

    async def get_customer_address(self, customer_id: int, address_id: int) -> Optional[CustomerAddress]:
        stmt = select(CustomerAddress).where(
            and_(
                CustomerAddress.id == address_id,
                CustomerAddress.user_id == customer_id,
                CustomerAddress.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def add_item(self, cart_id: int, menu_item_id: int, quantity: int) -> CartItem:
        # Check if item exists in cart already
        stmt = select(CartItem).where(
            and_(CartItem.cart_id == cart_id, CartItem.menu_item_id == menu_item_id)
        )
        result = await self.session.execute(stmt)
        existing_item = result.scalars().first()

        if existing_item:
            existing_item.quantity += quantity
            item = existing_item
        else:
            item = CartItem(cart_id=cart_id, menu_item_id=menu_item_id, quantity=quantity)
            self.session.add(item)
            
        await self.session.commit()
        await self.session.refresh(item)
        return item
        
    async def update_item_quantity(self, item_id: int, quantity: int) -> Optional[CartItem]:
        stmt = select(CartItem).where(CartItem.id == item_id)
        result = await self.session.execute(stmt)
        item = result.scalars().first()
        if item:
            item.quantity = quantity
            await self.session.commit()
            await self.session.refresh(item)
        return item

    async def remove_item(self, item_id: int) -> bool:
        stmt = select(CartItem).where(CartItem.id == item_id)
        result = await self.session.execute(stmt)
        item = result.scalars().first()
        if item:
            await self.session.delete(item)
            await self.session.commit()
            return True
        return False

    async def update_cart_context(self, cart: Cart, data: dict) -> Cart:
        for key, value in data.items():
            setattr(cart, key, value)
        await self.session.commit()
        await self.session.refresh(cart)
        return cart
