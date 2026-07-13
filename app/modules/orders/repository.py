from datetime import UTC, datetime
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, exists, or_
from sqlalchemy.orm import selectinload

from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.carts.models import Cart, CartStatus
from app.modules.rider_dispatch.models import OrderDispatchOffer

class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order_from_cart(self, cart: Cart, *, payment_method: str) -> Order:
        # Generate unique order number
        order_number = f"ORD-{str(uuid.uuid4())[:8].upper()}"

        now = datetime.now(UTC)

        order = Order(
            customer_id=cart.customer_id,
            restaurant_id=cart.restaurant_id,
            address_id=cart.address_id,
            order_number=order_number,
            status=OrderStatus.placed,
            total_price=cart.total_amount,
            payment_method=payment_method,
            delivery_address_text=(
                ", ".join(
                    part
                    for part in [
                        cart.address.address_line_1 if cart.address else None,
                        cart.address.area if cart.address else None,
                        cart.address.city if cart.address else None,
                    ]
                    if part
                )
                if cart.address
                else None
            ),
            delivery_recipient_name=cart.address.recipient_name if cart.address else None,
            delivery_phone_number=cart.address.phone_number if cart.address else None,
            delivery_latitude=cart.address.latitude if cart.address else None,
            delivery_longitude=cart.address.longitude if cart.address else None,
            coupon_code=cart.coupon_code,
            coupon_discount=cart.coupon_discount,
            delivery_fee=cart.delivery_fee,
            service_fee=cart.service_fee,
            tax_amount=cart.tax_amount,
            subtotal_amount=cart.subtotal_amount,
            needs_cutlery=cart.needs_cutlery,
            cooking_request=cart.cooking_request,
            delivery_instruction=cart.delivery_instruction,
            estimated_delivery_window=(
                f"{cart.restaurant.delivery_eta_min_minutes}-{cart.restaurant.delivery_eta_max_minutes} min"
                if cart.restaurant
                and cart.restaurant.delivery_eta_min_minutes
                and cart.restaurant.delivery_eta_max_minutes
                else "20-30 min"
            ),
            confirmed_at=now,
        )
        self.session.add(order)
        await self.session.flush()

        # Create order items
        for item in cart.items:
            if item.menu_item:
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=item.menu_item_id,
                    name=item.menu_item.name,
                    price=item.menu_item.price,
                    quantity=item.quantity
                )
                self.session.add(order_item)

        # Mark cart as checked out
        cart.status = CartStatus.checked_out

        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get_customer_orders(self, customer_id: int) -> List[Order]:
        stmt = select(Order).options(
            selectinload(Order.items),
            selectinload(Order.restaurant),
            selectinload(Order.address),
            selectinload(Order.rider),
        ).where(Order.customer_id == customer_id).order_by(Order.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_order_by_id(self, order_id: int, customer_id: int) -> Optional[Order]:
        stmt = select(Order).options(
            selectinload(Order.items),
            selectinload(Order.restaurant),
            selectinload(Order.address),
            selectinload(Order.rider),
        ).where(
            and_(Order.id == order_id, Order.customer_id == customer_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        stmt = select(Order).options(
            selectinload(Order.items),
            selectinload(Order.restaurant),
            selectinload(Order.customer),
            selectinload(Order.address),
            selectinload(Order.rider),
        ).where(Order.id == order_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_orders_by_rider(self, rider_user_id: int) -> List[Order]:
        now = datetime.now(UTC)
        has_pending_offer = exists(
            select(OrderDispatchOffer.id).where(
                OrderDispatchOffer.order_id == Order.id,
                OrderDispatchOffer.rider_user_id == rider_user_id,
                OrderDispatchOffer.status == "pending",
                or_(
                    OrderDispatchOffer.expires_at.is_(None),
                    OrderDispatchOffer.expires_at > now,
                ),
            )
        )
        stmt = select(Order).options(
            selectinload(Order.items),
            selectinload(Order.restaurant),
            selectinload(Order.customer),
            selectinload(Order.address),
            selectinload(Order.rider),
        ).where(
            or_(Order.rider_user_id == rider_user_id, has_pending_offer)
        ).order_by(Order.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
