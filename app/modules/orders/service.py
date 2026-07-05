from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.carts.models import Cart, CartItem, CartStatus
from app.modules.carts.repository import CartRepository
from app.modules.customers.models import CustomerAddress
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    CheckoutRequest,
    OrderAddressSnapshot,
    OrderItemResponse,
    OrderPricingBreakdown,
    OrderResponse,
    OrderTimelineEvent,
)


class OrderService:
    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)
        self.cart_repo = CartRepository(session)
        self.session = session

    @staticmethod
    def _build_timeline(order: Order) -> list[OrderTimelineEvent]:
        state_order = {
            OrderStatus.placed: 1,
            OrderStatus.preparing: 2,
            OrderStatus.delivered: 5,
            OrderStatus.cancelled: 6,
            OrderStatus.toPay: 0,
        }
        current_rank = state_order.get(order.status, 1)

        def event_state(rank: int, key: str) -> str:
            if order.status == OrderStatus.cancelled and key != "placed":
                return "cancelled"
            if rank < current_rank:
                return "completed"
            if rank == current_rank:
                return "current"
            return "upcoming"

        return [
            OrderTimelineEvent(
                key="placed",
                label="Order confirmed",
                state="completed",
                timestamp=order.confirmed_at or order.created_at,
                description="The restaurant has received your order.",
            ),
            OrderTimelineEvent(
                key="preparing",
                label="Food is preparing",
                state=event_state(2, "preparing"),
                timestamp=order.preparing_at,
                description="Your food is being freshly prepared.",
            ),
            OrderTimelineEvent(
                key="rider_assigned",
                label="Rider assigned",
                state=event_state(3, "rider_assigned"),
                timestamp=order.rider_assigned_at,
                description="A rider has been assigned to your order.",
            ),
            OrderTimelineEvent(
                key="picked_up",
                label="Pickup complete",
                state=event_state(4, "picked_up"),
                timestamp=order.picked_up_at,
                description="Your rider has picked up the order.",
            ),
            OrderTimelineEvent(
                key="delivered",
                label="Delivered",
                state=event_state(5, "delivered"),
                timestamp=order.delivered_at,
                description="Your order has been delivered successfully.",
            ),
        ]

    def _format_order_response(self, order: Order) -> OrderResponse:
        items = [
            OrderItemResponse(name=item.name, price=item.price, quantity=item.quantity)
            for item in order.items
        ]

        restaurant_name = order.restaurant.name if order.restaurant else "Unknown"
        restaurant_logo = order.restaurant.logo_url if order.restaurant and order.restaurant.logo_url else ""
        restaurant_tags = order.restaurant.primary_cuisine_label if order.restaurant and order.restaurant.primary_cuisine_label else ""
        delivery_time = order.estimated_delivery_window or "20-30 min"
        items_total = round(sum(item.price * item.quantity for item in order.items), 2)

        address = None
        if any(
            [
                order.address_id,
                order.delivery_recipient_name,
                order.delivery_phone_number,
                order.delivery_address_text,
            ]
        ):
            address = OrderAddressSnapshot(
                id=order.address_id,
                recipient_name=order.delivery_recipient_name,
                phone_number=order.delivery_phone_number,
                address_text=order.delivery_address_text,
                latitude=order.delivery_latitude,
                longitude=order.delivery_longitude,
            )

        return OrderResponse(
            restaurantName=restaurant_name,
            restaurantTags=restaurant_tags,
            restaurantLogo=restaurant_logo,
            deliveryTime=delivery_time,
            status=order.status,
            items=items,
            totalPrice=order.total_price,
            orderNumber=order.order_number,
            paymentMethod=order.payment_method,
            address=address,
            needsCutlery=order.needs_cutlery,
            cookingRequest=order.cooking_request,
            deliveryInstruction=order.delivery_instruction,
            pricing=OrderPricingBreakdown(
                items_total=items_total,
                coupon_discount=order.coupon_discount,
                delivery_fee=order.delivery_fee,
                service_fee=order.service_fee,
                tax_amount=order.tax_amount,
                subtotal_amount=order.subtotal_amount,
                total_amount=order.total_price,
            ),
            timeline=self._build_timeline(order),
        )

    async def _get_checkout_cart(self, customer_id: int, cart_id: int) -> Cart | None:
        stmt = (
            select(Cart)
            .options(
                selectinload(Cart.items).selectinload(CartItem.menu_item),
                selectinload(Cart.restaurant),
                selectinload(Cart.address),
            )
            .where(
                and_(
                    Cart.id == cart_id,
                    Cart.customer_id == customer_id,
                    Cart.status == CartStatus.active,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_customer_address(self, customer_id: int, address_id: int) -> CustomerAddress | None:
        return await self.cart_repo.get_customer_address(customer_id, address_id)

    async def checkout_cart(self, customer_id: int, cart_id: int, checkout_data: CheckoutRequest) -> OrderResponse:
        cart = await self._get_checkout_cart(customer_id, cart_id)
        if not cart or not cart.items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty or invalid")

        cart_updates: dict[str, object] = {}
        address_id = checkout_data.address_id or cart.address_id
        if address_id is not None:
            address = await self._get_customer_address(customer_id, address_id)
            if address is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid address.")
            cart_updates["address_id"] = address.id
        elif cart.address_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Delivery address is required.")

        if checkout_data.coupon_code is not None:
            cart_updates["coupon_code"] = checkout_data.coupon_code.strip().upper() if checkout_data.coupon_code else None
        if checkout_data.needs_cutlery is not None:
            cart_updates["needs_cutlery"] = checkout_data.needs_cutlery
        if checkout_data.cooking_request is not None:
            cart_updates["cooking_request"] = checkout_data.cooking_request
        if checkout_data.delivery_instruction is not None:
            cart_updates["delivery_instruction"] = checkout_data.delivery_instruction

        if cart_updates:
            await self.cart_repo.update_cart_context(cart, cart_updates)
            cart = await self._get_checkout_cart(customer_id, cart_id)
            if cart is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        from app.modules.carts.service import CartService

        cart_service = CartService(self.session)
        cart_service._recalculate_cart_totals(cart)
        await self.cart_repo.update_cart_context(
            cart,
            {
                "coupon_discount": cart.coupon_discount,
                "delivery_fee": cart.delivery_fee,
                "service_fee": cart.service_fee,
                "tax_amount": cart.tax_amount,
                "subtotal_amount": cart.subtotal_amount,
                "total_amount": cart.total_amount,
            },
        )
        cart = await self._get_checkout_cart(customer_id, cart_id)
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        order = await self.repo.create_order_from_cart(cart, payment_method=checkout_data.payment_method)

        if order.status == OrderStatus.placed:
            order.preparing_at = datetime.now(UTC)
            await self.session.commit()
            await self.session.refresh(order)

        order = await self.repo.get_order_by_id(order.id, customer_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return self._format_order_response(order)

    async def get_my_orders(self, customer_id: int) -> list[OrderResponse]:
        orders = await self.repo.get_customer_orders(customer_id)
        return [self._format_order_response(order) for order in orders]

    async def get_order(self, customer_id: int, order_id: int) -> OrderResponse:
        order = await self.repo.get_order_by_id(order_id, customer_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return self._format_order_response(order)
