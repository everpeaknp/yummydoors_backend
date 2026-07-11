import logging
from datetime import UTC, datetime
from fastapi import HTTPException, status
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import User, UserRole
from app.modules.analytics.service import apply_completed_order_loyalty
from app.modules.carts.models import Cart, CartItem, CartStatus
from app.modules.carts.repository import CartRepository
from app.modules.catalog.models import MenuItem
from app.modules.customers.models import CustomerAddress
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    CheckoutRequest,
    OrderAddressSnapshot,
    OrderItemResponse,
    OrderPricingBreakdown,
    OrderResponse,
    OrderSummaryRequest,
    OrderSummaryResponse,
    OrderTimelineEvent,
    MerchantOrderResponse,
    RiderSummaryResponse,
    UserSnapshot,
)


class OrderService:
    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)
        self.cart_repo = CartRepository(session)
        self.session = session

    @staticmethod
    def _build_timeline(order: Order) -> list[OrderTimelineEvent]:
        if order.status == OrderStatus.cancelled:
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
                    state="cancelled",
                    timestamp=order.preparing_at,
                    description="Your food was not prepared because the order was cancelled.",
                ),
                OrderTimelineEvent(
                    key="rider_assigned",
                    label="Rider assigned",
                    state="cancelled",
                    timestamp=order.rider_assigned_at,
                    description="No rider was assigned before cancellation.",
                ),
                OrderTimelineEvent(
                    key="picked_up",
                    label="Pickup complete",
                    state="cancelled",
                    timestamp=order.picked_up_at,
                    description="The order was cancelled before pickup.",
                ),
                OrderTimelineEvent(
                    key="delivered",
                    label="Delivered",
                    state="cancelled",
                    timestamp=order.delivered_at,
                    description="The order was cancelled before delivery.",
                ),
            ]

        current_rank = 1
        if order.delivered_at or order.status == OrderStatus.delivered:
            current_rank = 5
        elif order.picked_up_at:
            current_rank = 4
        elif order.rider_assigned_at:
            current_rank = 3
        elif order.preparing_at or order.status == OrderStatus.preparing:
            current_rank = 2

        def event_state(rank: int) -> str:
            if rank < current_rank:
                return "completed"
            if rank == current_rank:
                return "current"
            return "upcoming"

        return [
            OrderTimelineEvent(
                key="placed",
                label="Order confirmed",
                state=event_state(1),
                timestamp=order.confirmed_at or order.created_at,
                description="The restaurant has received your order.",
            ),
            OrderTimelineEvent(
                key="preparing",
                label="Food is preparing",
                state=event_state(2),
                timestamp=order.preparing_at,
                description="Your food is being freshly prepared.",
            ),
            OrderTimelineEvent(
                key="rider_assigned",
                label="Rider assigned",
                state=event_state(3),
                timestamp=order.rider_assigned_at,
                description="A rider has been assigned to your order.",
            ),
            OrderTimelineEvent(
                key="picked_up",
                label="Pickup complete",
                state=event_state(4),
                timestamp=order.picked_up_at,
                description="Your rider has picked up the order.",
            ),
            OrderTimelineEvent(
                key="delivered",
                label="Delivered",
                state=event_state(5),
                timestamp=order.delivered_at,
                description="Your order has been delivered successfully.",
            ),
        ]

    @staticmethod
    def _snapshot_user(user: User | None) -> UserSnapshot | None:
        if user is None:
            return None
        return UserSnapshot(
            id=user.id,
            full_name=user.full_name,
            phone=user.phone,
            avatar_url=user.avatar_url,
        )

    def _format_order_response(self, order: Order) -> OrderResponse:
        items = [
            OrderItemResponse(name=item.name, price=item.price, quantity=item.quantity)
            for item in order.items
        ]

        restaurant_name = order.restaurant.name if order.restaurant else "Unknown"
        restaurant_logo = (
            order.restaurant.logo_url if order.restaurant and order.restaurant.logo_url else ""
        )
        restaurant_tags = (
            order.restaurant.primary_cuisine_label
            if order.restaurant and order.restaurant.primary_cuisine_label
            else ""
        )
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
            id=order.id,
            restaurantId=order.restaurant_id,
            restaurantName=restaurant_name,
            restaurantSlug=order.restaurant.slug if order.restaurant else "",
            restaurantLatitude=order.restaurant.latitude if order.restaurant else None,
            restaurantLongitude=order.restaurant.longitude if order.restaurant else None,
            restaurantTags=restaurant_tags,
            restaurantLogo=restaurant_logo,
            deliveryTime=delivery_time,
            status=order.status,
            items=items,
            totalPrice=order.total_price,
            orderNumber=order.order_number,
            paymentMethod=order.payment_method,
            address=address,
            rider=self._snapshot_user(order.rider),
            needsCutlery=order.needs_cutlery,
            cookingRequest=order.cooking_request,
            deliveryInstruction=order.delivery_instruction,
            confirmedAt=order.confirmed_at,
            preparingAt=order.preparing_at,
            riderAssignedAt=order.rider_assigned_at,
            pickedUpAt=order.picked_up_at,
            deliveredAt=order.delivered_at,
            cancelledAt=order.cancelled_at,
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

    def _format_merchant_order_response(self, order: Order) -> MerchantOrderResponse:
        items = [
            OrderItemResponse(name=item.name, price=item.price, quantity=item.quantity)
            for item in order.items
        ]
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

        return MerchantOrderResponse(
            id=order.id,
            customerId=order.customer_id,
            restaurantId=order.restaurant_id,
            orderNumber=order.order_number,
            restaurantName=order.restaurant.name if order.restaurant else "Unknown",
            restaurantSlug=order.restaurant.slug if order.restaurant else None,
            restaurantLatitude=order.restaurant.latitude if order.restaurant else None,
            restaurantLongitude=order.restaurant.longitude if order.restaurant else None,
            customerName=order.customer.full_name if order.customer else "Unknown",
            date=order.created_at.strftime("%d/%m/%Y"),
            status=order.status,
            totalPrice=order.total_price,
            items=items,
            deliveryTime=order.estimated_delivery_window or "20-30 min",
            address=address,
            rider=self._snapshot_user(order.rider),
            confirmedAt=order.confirmed_at,
            preparingAt=order.preparing_at,
            riderAssignedAt=order.rider_assigned_at,
            pickedUpAt=order.picked_up_at,
            deliveredAt=order.delivered_at,
            cancelledAt=order.cancelled_at,
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

    async def _get_customer_address(
        self, customer_id: int, address_id: int
    ) -> CustomerAddress | None:
        return await self.cart_repo.get_customer_address(customer_id, address_id)

    async def checkout_cart(
        self, customer_id: int, cart_id: int, checkout_data: CheckoutRequest
    ) -> OrderResponse:
        cart = await self._get_checkout_cart(customer_id, cart_id)
        if not cart or not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty or invalid"
            )

        cart_updates: dict[str, object] = {}
        address_id = checkout_data.address_id or cart.address_id
        if address_id is not None:
            address = await self._get_customer_address(customer_id, address_id)
            if address is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid address."
                )
            cart_updates["address_id"] = address.id
        elif cart.address_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Delivery address is required."
            )

        if checkout_data.coupon_code is not None:
            cart_updates["coupon_code"] = (
                checkout_data.coupon_code.strip().upper() if checkout_data.coupon_code else None
            )
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

        order = await self.repo.create_order_from_cart(
            cart, payment_method=checkout_data.payment_method
        )

        # Increment popularity_score on each ordered item (tracks sales count)
        item_quantities: dict[int, int] = {}
        for cart_item in cart.items:
            if cart_item.menu_item_id is not None:
                item_quantities[cart_item.menu_item_id] = (
                    item_quantities.get(cart_item.menu_item_id, 0) + cart_item.quantity
                )
        for menu_item_id, qty in item_quantities.items():
            await self.session.execute(
                update(MenuItem)
                .where(MenuItem.id == menu_item_id)
                .values(popularity_score=MenuItem.popularity_score + qty)
            )

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

    async def calculate_summary(self, payload: OrderSummaryRequest) -> OrderSummaryResponse:
        from app.modules.catalog.models import MenuItem, MenuModifierItem

        items_total = 0.0
        response_items = []

        if payload.items:
            item_ids = [req_item.menu_item_id for req_item in payload.items]
            stmt = select(MenuItem).where(MenuItem.id.in_(item_ids))
            result = await self.session.execute(stmt)
            menu_items_map = {item.id: item for item in result.scalars().all()}

            all_mod_ids = []
            for req_item in payload.items:
                all_mod_ids.extend(req_item.modifier_ids)

            modifiers_map = {}
            if all_mod_ids:
                mod_stmt = select(MenuModifierItem).where(MenuModifierItem.id.in_(all_mod_ids))
                mod_result = await self.session.execute(mod_stmt)
                modifiers_map = {mod.id: mod for mod in mod_result.scalars().all()}

            for req_item in payload.items:
                menu_item = menu_items_map.get(req_item.menu_item_id)
                if not menu_item:
                    continue

                item_price = menu_item.price
                item_name = menu_item.name

                if req_item.modifier_ids:
                    mod_names = []
                    for mod_id in req_item.modifier_ids:
                        mod = modifiers_map.get(mod_id)
                        if mod:
                            item_price += mod.price_adjustment
                            mod_names.append(mod.name)
                    if mod_names:
                        item_name += f" ({', '.join(mod_names)})"

                line_total = item_price * req_item.quantity
                items_total += line_total

                response_items.append(
                    OrderItemResponse(name=item_name, price=item_price, quantity=req_item.quantity)
                )

        # Basic fixed pricing logic (should ideally come from restaurant or distance)
        delivery_fee = 100.0 if items_total > 0 else 0.0
        coupon_discount = 0.0
        if payload.coupon_code == "DISCOUNT50":
            coupon_discount = 50.0

        subtotal = max(0, items_total - coupon_discount + delivery_fee)

        pricing = OrderPricingBreakdown(
            items_total=items_total,
            coupon_discount=coupon_discount,
            delivery_fee=delivery_fee,
            service_fee=0.0,
            tax_amount=0.0,
            subtotal_amount=subtotal,
            total_amount=subtotal,
        )

        return OrderSummaryResponse(items=response_items, pricing=pricing)

    async def get_merchant_orders(self, merchant_user_id: int) -> list[MerchantOrderResponse]:
        restaurant_id = await self._get_active_merchant_restaurant_id(merchant_user_id)
        if restaurant_id is None:
            return []

        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.customer),
                selectinload(Order.restaurant),
                selectinload(Order.address),
                selectinload(Order.rider),
            )
            .where(Order.restaurant_id == restaurant_id)
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        orders = result.scalars().all()

        return [self._format_merchant_order_response(order) for order in orders]

    async def get_rider_orders(self, rider_user_id: int) -> list[MerchantOrderResponse]:
        orders = await self.repo.get_orders_by_rider(rider_user_id)
        return [self._format_merchant_order_response(order) for order in orders]

    async def list_restaurant_riders(self, merchant_user_id: int) -> list[RiderSummaryResponse]:
        restaurant_id = await self._get_active_merchant_restaurant_id(merchant_user_id)
        if restaurant_id is None:
            return []

        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role),
                selectinload(User.restaurant_assignments),
            )
            .where(User.is_active.is_(True))
        )
        result = await self.session.execute(stmt)
        users = result.scalars().unique().all()

        riders: list[RiderSummaryResponse] = []
        for user in users:
            if not self._user_has_rider_access(user, restaurant_id):
                continue
            riders.append(
                RiderSummaryResponse(
                    id=user.id,
                    full_name=user.full_name,
                    phone=user.phone,
                    avatar_url=user.avatar_url,
                    restaurant_ids=sorted(
                        {
                            assignment.restaurant_id
                            for assignment in user.restaurant_assignments
                            if assignment.restaurant_id is not None
                        }
                    ),
                )
            )
        return riders

    async def update_merchant_order_status(self, merchant_user_id: int, order_id: int, new_status: OrderStatus) -> MerchantOrderResponse:
        restaurant_id = await self._get_active_merchant_restaurant_id(merchant_user_id)
        if not restaurant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active restaurant context.")

        order = await self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
            
        if order.restaurant_id != restaurant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to modify this order.")

        previous_status = order.status
        # Update order status
        order.status = new_status
        now = datetime.now(UTC)
        
        if new_status == OrderStatus.preparing:
            order.preparing_at = now
        elif new_status == OrderStatus.delivered:
            order.delivered_at = now
        elif new_status == OrderStatus.cancelled:
            order.cancelled_at = now

        if new_status == OrderStatus.delivered and previous_status != OrderStatus.delivered:
            try:
                await apply_completed_order_loyalty(self.session, order)
            except Exception:
                logging.getLogger("yummy.order").exception(
                    "Failed to update customer loyalty for order %s", order.id
                )

        await self.session.commit()
        await self.session.refresh(order)
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order)

    async def assign_rider_to_order(
        self,
        merchant_user_id: int,
        order_id: int,
        rider_user_id: int,
    ) -> MerchantOrderResponse:
        restaurant_id = await self._get_active_merchant_restaurant_id(merchant_user_id)
        if not restaurant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active restaurant context.")

        order = await self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if order.restaurant_id != restaurant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to modify this order.")
        if order.status == OrderStatus.cancelled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled orders cannot be assigned.")
        if order.status == OrderStatus.delivered:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Delivered orders cannot be assigned.")

        rider = await self._load_user_with_roles(rider_user_id)
        if rider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found.")
        if not self._user_has_rider_access(rider, restaurant_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected rider is not assigned to this restaurant.")

        now = datetime.now(UTC)
        order.rider_user_id = rider_user_id
        order.rider_assigned_at = now
        if order.status == OrderStatus.placed:
            order.status = OrderStatus.preparing
            order.preparing_at = order.preparing_at or now

        await self.session.commit()
        await self.session.refresh(order)
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order)

    async def rider_claim_order(self, rider_user_id: int, order_id: int) -> MerchantOrderResponse:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if order.rider_user_id and order.rider_user_id != rider_user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already assigned to another rider.")

        rider = await self._load_user_with_roles(rider_user_id)
        if rider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found.")
        if not self._user_has_rider_access(rider, order.restaurant_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this restaurant.")

        now = datetime.now(UTC)
        order.rider_user_id = rider_user_id
        order.rider_assigned_at = order.rider_assigned_at or now
        if order.status == OrderStatus.placed:
            order.status = OrderStatus.preparing
            order.preparing_at = order.preparing_at or now
        await self.session.commit()
        await self.session.refresh(order)
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order)

    async def rider_mark_picked_up(self, rider_user_id: int, order_id: int) -> MerchantOrderResponse:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if order.rider_user_id != rider_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This order is not assigned to you.")
        if order.status == OrderStatus.cancelled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled orders cannot be updated.")
        order.picked_up_at = order.picked_up_at or datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(order)
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order)

    async def rider_mark_delivered(self, rider_user_id: int, order_id: int) -> MerchantOrderResponse:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if order.rider_user_id != rider_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This order is not assigned to you.")
        if order.status == OrderStatus.cancelled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled orders cannot be updated.")
        previous_status = order.status
        now = datetime.now(UTC)
        order.picked_up_at = order.picked_up_at or now
        order.delivered_at = now
        order.status = OrderStatus.delivered
        if previous_status != OrderStatus.delivered:
            try:
                await apply_completed_order_loyalty(self.session, order)
            except Exception:
                logging.getLogger("yummy.order").exception(
                    "Failed to update customer loyalty for order %s", order.id
                )
        await self.session.commit()
        await self.session.refresh(order)
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order)

    async def _get_active_merchant_restaurant_id(self, merchant_user_id: int) -> int | None:
        from app.modules.workspaces.repository import WorkspaceRepository

        workspace_repo = WorkspaceRepository(self.session)
        workspace = await workspace_repo.get_active_workspace(merchant_user_id)
        if not workspace or workspace.workspace_type != "merchant":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active workspace is not a merchant workspace.",
            )
        return workspace.primary_restaurant_id

    async def _load_user_with_roles(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role),
                selectinload(User.restaurant_assignments),
            )
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _user_has_rider_access(user: User, restaurant_id: int) -> bool:
        role_codes = {user_role.role.code for user_role in user.roles}
        if "rider" not in role_codes:
            return False

        scoped_restaurant_ids = {
            user_role.restaurant_id
            for user_role in user.roles
            if user_role.role.code == "rider" and user_role.restaurant_id is not None
        }
        assignment_restaurant_ids = {
            assignment.restaurant_id
            for assignment in user.restaurant_assignments
            if assignment.restaurant_id is not None and assignment.assignment_type == "rider"
        }
        active_restaurant_id = user.active_restaurant_id
        all_restaurant_ids = scoped_restaurant_ids | assignment_restaurant_ids
        if restaurant_id in all_restaurant_ids:
            return True
        if active_restaurant_id == restaurant_id:
            return True
        return False
