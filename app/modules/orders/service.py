import logging
from datetime import UTC, datetime
from fastapi import HTTPException, status
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.geo import haversine_km
from app.modules.auth.models import User, UserRole
from app.modules.analytics.service import apply_completed_order_loyalty
from app.modules.carts.models import Cart, CartItem, CartStatus
from app.modules.carts.repository import CartRepository
from app.modules.catalog.models import MenuItem, MenuModifierGroup
from app.modules.customers.models import CustomerAddress
from app.modules.orders.models import Order, OrderStatus, OrderStatusEvent
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
from app.modules.restaurant_settlements.schemas import RestaurantSettlementResponse
from app.modules.restaurant_settlements.service import RestaurantSettlementService
from app.modules.rider_dispatch.service import RiderDispatchService
from app.modules.rider_payouts.service import RiderPayoutService


# Explicit, enforced state machine for merchant-driven status changes.
# `toPay` and `placed` are effectively the same "not yet being cooked" stage
# for this purpose; delivered/cancelled are terminal.
_ALLOWED_MERCHANT_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.toPay: {OrderStatus.placed, OrderStatus.preparing, OrderStatus.cancelled},
    OrderStatus.placed: {OrderStatus.preparing, OrderStatus.cancelled},
    OrderStatus.preparing: {OrderStatus.delivered, OrderStatus.cancelled},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
}

# Customers may self-serve cancel only before the restaurant has started
# preparing the order — matches Uber Eats' policy (free cancellation only
# up until the merchant accepts). Once preparing/delivered/already
# cancelled, cancellation must go through the restaurant/support instead.
_CUSTOMER_CANCELLABLE_STATUSES: set[OrderStatus] = {OrderStatus.toPay, OrderStatus.placed}


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

    # Single source of truth for the customer-facing sub-status derived from
    # timestamps — OrderStatus itself only has placed/preparing/delivered/
    # cancelled, so every client used to reverse-engineer "rider assigned" /
    # "picked up" / "on the way" from raw timestamp fields independently.
    # Centralizing it here means clients read one field instead of
    # re-implementing this logic (and risking drift/bugs, as already
    # happened once this session).
    @staticmethod
    def _derive_sub_status(order: Order) -> str:
        if order.status == OrderStatus.cancelled:
            return "cancelled"
        if order.status == OrderStatus.delivered or order.delivered_at:
            return "delivered"
        if order.picked_up_at:
            return "on_the_way"
        if order.rider_assigned_at:
            return "rider_assigned"
        if order.preparing_at or order.status == OrderStatus.preparing:
            return "preparing"
        return "placed"

    # Real-time ETA estimate from the rider's live GPS to whichever stop is
    # next (the restaurant if not yet picked up, the delivery address once
    # it's picked up) — replaces the static "20-30 min" snapshot taken once
    # at checkout, which never moved again no matter how close the rider
    # actually got. Straight-line distance over an assumed urban delivery
    # speed rather than a routed duration, to avoid an OSRM round-trip on
    # every order-detail fetch; a small buffer keeps it from reading
    # unrealistically low right as the rider arrives.
    _AVERAGE_DELIVERY_SPEED_KMH = 18.0

    @classmethod
    def _live_eta_minutes(cls, order: Order) -> int | None:
        if order.status in {OrderStatus.delivered, OrderStatus.cancelled}:
            return None
        rider = order.rider
        if rider is None or rider.current_latitude is None or rider.current_longitude is None:
            return None

        if order.picked_up_at:
            target_lat, target_lon = order.delivery_latitude, order.delivery_longitude
        else:
            target_lat = order.restaurant.latitude if order.restaurant else None
            target_lon = order.restaurant.longitude if order.restaurant else None
        if target_lat is None or target_lon is None:
            return None

        distance_km = haversine_km(rider.current_latitude, rider.current_longitude, target_lat, target_lon)
        minutes = (distance_km / cls._AVERAGE_DELIVERY_SPEED_KMH) * 60
        return max(2, round(minutes) + 2)

    @classmethod
    def _live_eta_text(cls, order: Order) -> str | None:
        minutes = cls._live_eta_minutes(order)
        if minutes is None:
            return None
        if order.picked_up_at:
            return f"Arriving in ~{minutes} min"
        return f"Rider ~{minutes} min from the restaurant"

    @staticmethod
    def _snapshot_user(user: User | None) -> UserSnapshot | None:
        if user is None:
            return None
        return UserSnapshot(
            id=user.id,
            full_name=user.full_name,
            phone=user.phone,
            avatar_url=user.avatar_url,
            current_latitude=user.current_latitude,
            current_longitude=user.current_longitude,
            current_location_updated_at=user.current_location_updated_at,
        )

    def _format_order_response(self, order: Order) -> OrderResponse:
        items = [
            OrderItemResponse(
                name=item.name,
                price=item.price,
                quantity=item.quantity,
                modifier_selections=item.modifier_snapshot,
                add_on_selections=item.add_on_snapshot,
            )
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
        restaurant_phone = order.restaurant.contact_phone if order.restaurant else None
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
            restaurantPhone=restaurant_phone,
            deliveryTime=delivery_time,
            status=order.status,
            subStatus=self._derive_sub_status(order),
            liveEtaMinutes=self._live_eta_minutes(order),
            liveEtaText=self._live_eta_text(order),
            items=items,
            totalPrice=order.total_price,
            orderNumber=order.order_number,
            paymentMethod=order.payment_method,
            paymentStatus=order.payment_status,
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
            riderAssignmentState=order.rider_assignment_state,
            riderAssignmentTier=order.rider_assignment_tier,
            riderOfferExpiresAt=order.rider_offer_expires_at,
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

    def _format_merchant_order_response(
        self,
        order: Order,
        rider_offer=None,
    ) -> MerchantOrderResponse:
        items = [
            OrderItemResponse(
                name=item.name,
                price=item.price,
                quantity=item.quantity,
                modifier_selections=item.modifier_snapshot,
                add_on_selections=item.add_on_snapshot,
            )
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
            riderDispatchPolicy=order.restaurant.rider_dispatch_policy if order.restaurant else "ranked",
            customerName=order.customer.full_name if order.customer else "Unknown",
            date=order.created_at.strftime("%d/%m/%Y"),
            status=order.status,
            subStatus=self._derive_sub_status(order),
            liveEtaMinutes=self._live_eta_minutes(order),
            liveEtaText=self._live_eta_text(order),
            paymentStatus=order.payment_status,
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
            riderAssignmentState=order.rider_assignment_state,
            riderAssignmentTier=order.rider_assignment_tier,
            riderOfferExpiresAt=order.rider_offer_expires_at,
            riderOfferId=rider_offer.id if rider_offer else None,
            riderOfferTier=rider_offer.tier if rider_offer else None,
        )

    async def _get_checkout_cart(self, customer_id: int, cart_id: int) -> Cart | None:
        stmt = (
            select(Cart)
            .options(
                selectinload(Cart.items)
                .selectinload(CartItem.menu_item)
                .selectinload(MenuItem.modifier_groups)
                .selectinload(MenuModifierGroup.items),
                selectinload(Cart.items).selectinload(CartItem.menu_item).selectinload(MenuItem.add_ons),
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
        await cart_service._recalculate_cart_totals(cart)
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
            cart,
            payment_method=checkout_data.payment_method,
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

        if cart.coupon_code and cart.coupon_discount:
            from app.modules.promotions.service import PromotionService

            try:
                await PromotionService(self.session).redeem(
                    code=cart.coupon_code,
                    customer_id=customer_id,
                    order_id=order.id,
                    discount_amount=cart.coupon_discount,
                )
            except HTTPException:
                # The order is already placed and priced with the discount
                # already applied — a coupon usage-limit race lost here just
                # means this redemption isn't counted against the limit, not
                # that the order itself should fail.
                logging.getLogger("yummy.order").warning(
                    "coupon redemption bookkeeping failed for order %s (code=%s)", order.id, cart.coupon_code
                )

        order = await self.repo.get_order_by_id(order.id, customer_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        # Private-only restaurants have their own dedicated rider team, so
        # there's no reason to wait for the merchant to start preparing
        # before dispatching — and assign_rider_to_order already tells
        # merchants "the order is sent automatically" the moment they try to
        # assign manually. Without this, that message was a false promise:
        # dispatch_next_offer was only ever called on the preparing
        # transition, so an order could sit fully undispatched — invisible
        # to every rider — until the merchant happened to advance its status.
        if order.restaurant is not None and order.restaurant.rider_dispatch_policy == "private_only":
            dispatch_service = RiderDispatchService(self.session)
            await dispatch_service.dispatch_next_offer(order_id=order.id)
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

    async def cancel_order(
        self, customer_id: int, order_id: int, reason: str | None = None
    ) -> OrderResponse:
        order = await self.repo.get_order_by_id(order_id, customer_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status not in _CUSTOMER_CANCELLABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This order can no longer be cancelled from the app — the restaurant "
                    "has already started preparing it. Please contact the restaurant or "
                    "support for help."
                ),
            )

        previous_status = order.status
        now = datetime.now(UTC)
        # Conditional UPDATE (compare-and-swap on the still-cancellable
        # statuses) instead of a plain ORM mutation + commit: the merchant
        # could be moving this order to "preparing" at the same instant, and
        # whichever write commits first must win.
        result = await self.session.execute(
            update(Order)
            .where(
                Order.id == order_id,
                Order.customer_id == customer_id,
                Order.status.in_(_CUSTOMER_CANCELLABLE_STATUSES),
            )
            .values(status=OrderStatus.cancelled, cancelled_at=now, rider_offer_expires_at=None)
        )
        if result.rowcount != 1:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This order can no longer be cancelled from the app — the restaurant "
                    "has already started preparing it. Please contact the restaurant or "
                    "support for help."
                ),
            )

        self.session.add(
            OrderStatusEvent(
                order_id=order.id,
                actor_user_id=customer_id,
                previous_status=previous_status.value,
                new_status=OrderStatus.cancelled.value,
                source="customer",
                note=reason,
            )
        )
        await self.session.commit()
        order = await self.repo.get_order_by_id(order_id, customer_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return self._format_order_response(order)

    async def calculate_summary(self, payload: OrderSummaryRequest) -> OrderSummaryResponse:
        from app.modules.catalog.models import MenuAddOn, MenuItem

        items_total = 0.0
        response_items = []

        if payload.items:
            item_ids = [req_item.menu_item_id for req_item in payload.items]
            stmt = (
                select(MenuItem)
                .options(
                    selectinload(MenuItem.modifier_groups).selectinload(MenuModifierGroup.items),
                    selectinload(MenuItem.add_ons),
                )
                .where(
                    MenuItem.id.in_(item_ids),
                    MenuItem.restaurant_id == payload.restaurant_id,
                )
            )
            result = await self.session.execute(stmt)
            menu_items_map = {item.id: item for item in result.scalars().all()}

            all_add_on_ids = [
                selection["add_on_id"]
                for req_item in payload.items
                for selection in req_item.add_on_selections
            ]

            add_ons_map = {}
            if all_add_on_ids:
                add_on_result = await self.session.execute(
                    select(MenuAddOn).where(MenuAddOn.id.in_(all_add_on_ids))
                )
                add_ons_map = {add_on.id: add_on for add_on in add_on_result.scalars().all()}

            for req_item in payload.items:
                menu_item = menu_items_map.get(req_item.menu_item_id)
                if not menu_item:
                    raise HTTPException(status_code=400, detail="Invalid menu item.")

                item_price = menu_item.price
                item_name = menu_item.name

                if req_item.modifier_ids:
                    modifier_options = {
                        option.id: option
                        for group in menu_item.modifier_groups
                        for option in group.items
                    }
                    mod_names = []
                    for mod_id in req_item.modifier_ids:
                        mod = modifier_options.get(mod_id)
                        if mod is None or not mod.is_available:
                            raise HTTPException(status_code=400, detail="Invalid or unavailable modifier.")
                        item_price += mod.price_adjustment
                        mod_names.append(mod.name)
                    if mod_names:
                        item_name += f" ({', '.join(mod_names)})"
                for selection in req_item.add_on_selections:
                    add_on = add_ons_map.get(selection["add_on_id"])
                    quantity = selection.get("quantity", 1)
                    if (
                        add_on is None
                        or add_on.menu_item_id != menu_item.id
                        or not add_on.is_available
                        or quantity < 1
                        or quantity > add_on.max_quantity
                    ):
                        raise HTTPException(status_code=400, detail="Invalid or unavailable add-on selection.")
                    item_price += add_on.price * quantity
                    item_name += f" + {add_on.name}"

                line_total = item_price * req_item.quantity
                items_total += line_total

                response_items.append(
                    OrderItemResponse(name=item_name, price=item_price, quantity=req_item.quantity)
                )

        coupon_discount = 0.0
        free_delivery = False
        if payload.coupon_code:
            from app.modules.promotions.service import PromotionService

            quote = await PromotionService(self.session).quote_discount(
                code=payload.coupon_code,
                restaurant_id=payload.restaurant_id,
                customer_id=None,
                items_total=items_total,
            )
            coupon_discount = quote.discount_amount
            free_delivery = quote.free_delivery

        delivery_fee = 0.0 if free_delivery else (100.0 if items_total > 0 else 0.0)
        service_fee = round(items_total * 0.05, 2)
        tax_amount = round(items_total * 0.13, 2)
        subtotal = round(items_total - coupon_discount, 2)
        total = max(round(subtotal + delivery_fee + service_fee + tax_amount, 2), 0.0)

        pricing = OrderPricingBreakdown(
            items_total=items_total,
            coupon_discount=coupon_discount,
            delivery_fee=delivery_fee,
            service_fee=service_fee,
            tax_amount=tax_amount,
            subtotal_amount=subtotal,
            total_amount=total,
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
        dispatch_service = RiderDispatchService(self.session)
        offers = await dispatch_service.list_pending_offers_for_rider(
            rider_user_id=rider_user_id,
        )
        offers_by_order = {offer.order_id: offer for offer in offers}
        return [
            self._format_merchant_order_response(
                order,
                rider_offer=offers_by_order.get(order.id),
            )
            for order in orders
        ]

    async def list_restaurant_riders(self, merchant_user_id: int) -> list[RiderSummaryResponse]:
        restaurant_id = await self._get_active_merchant_restaurant_id(merchant_user_id)
        if restaurant_id is None:
            return []
        dispatch_service = RiderDispatchService(self.session)
        candidates = await dispatch_service.list_candidates(
            merchant_user_id=merchant_user_id,
            restaurant_id=restaurant_id,
        )
        return [
            RiderSummaryResponse(
                id=item.id,
                full_name=item.full_name,
                phone=item.phone,
                avatar_url=item.avatar_url,
                assignment_type=item.assignment_type,
                rider_work_mode=item.rider_work_mode,
                is_accepting_offers=item.is_accepting_offers,
                busy=item.busy,
                distance_km=item.distance_km,
                current_latitude=item.current_latitude,
                current_longitude=item.current_longitude,
                restaurant_ids=[],
            )
            for item in candidates
        ]

    async def list_merchant_settlements(self, merchant_user_id: int) -> list[RestaurantSettlementResponse]:
        restaurant_id = await self._get_active_merchant_restaurant_id(merchant_user_id)
        if restaurant_id is None:
            return []
        return await RestaurantSettlementService(self.session).list_for_restaurant(restaurant_id)

    async def update_merchant_order_status(
        self,
        merchant_user_id: int,
        order_id: int,
        new_status: OrderStatus,
        reason: str | None = None,
    ) -> MerchantOrderResponse:
        restaurant_id = await self._get_active_merchant_restaurant_id(merchant_user_id)
        if not restaurant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active restaurant context.")

        order = await self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        if order.restaurant_id != restaurant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to modify this order.")

        previous_status = order.status
        allowed_next = _ALLOWED_MERCHANT_TRANSITIONS.get(previous_status, set())
        if new_status != previous_status and new_status not in allowed_next:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot move an order from {previous_status.value} to {new_status.value}.",
            )

        completed_without_rider = False
        if new_status == OrderStatus.delivered:
            completed_without_rider = self._validate_merchant_delivery(order, reason=reason)

        # Update order status
        order.status = new_status
        now = datetime.now(UTC)

        if new_status == OrderStatus.preparing:
            order.preparing_at = now
            dispatch_service = RiderDispatchService(self.session)
            await dispatch_service.dispatch_next_offer(order_id=order.id)
        elif new_status == OrderStatus.delivered:
            order.delivered_at = now
            order.rider_offer_expires_at = None
        elif new_status == OrderStatus.cancelled:
            order.cancelled_at = now
            order.rider_offer_expires_at = None

        if new_status == OrderStatus.delivered and previous_status != OrderStatus.delivered:
            try:
                await apply_completed_order_loyalty(self.session, order)
            except Exception:
                logging.getLogger("yummy.order").exception(
                    "Failed to update customer loyalty for order %s", order.id
                )
            try:
                await RiderPayoutService(self.session).compute_payout_for_order(order)
            except Exception:
                logging.getLogger("yummy.order").exception(
                    "Failed to compute rider payout for order %s", order.id
                )
            try:
                await RestaurantSettlementService(self.session).compute_settlement_for_order(order)
            except Exception:
                logging.getLogger("yummy.order").exception(
                    "Failed to compute restaurant settlement for order %s", order.id
                )

        if new_status != previous_status:
            note = reason
            if completed_without_rider and not note:
                note = "Marked delivered by merchant without an assigned rider."
            self.session.add(
                OrderStatusEvent(
                    order_id=order.id,
                    actor_user_id=merchant_user_id,
                    previous_status=previous_status.value,
                    new_status=new_status.value,
                    source="merchant",
                    note=note,
                )
            )

        await self.session.commit()
        await self.session.refresh(order)
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order)

    @staticmethod
    def _validate_merchant_delivery(order: Order, *, reason: str | None) -> bool:
        """Returns True if this is a merchant completing the order without
        ever assigning a rider — a deliberate escape path (e.g. the merchant
        delivered it themselves, or delivery wasn't needed). This path
        requires an explicit reason so it's auditable, not a silent status
        flip.
        """
        if order.rider_user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assigned riders must mark orders as delivered.",
            )
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "A reason is required to complete an order without an assigned rider "
                    "(e.g. self-delivery, pickup, or delivery not needed)."
                ),
            )
        return True

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
        if order.restaurant and order.restaurant.rider_dispatch_policy == "private_only":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Private rider dispatch is enabled. The order is sent to the private rider team automatically.")

        rider = await self._load_user_with_roles(rider_user_id)
        if rider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found.")
        
        is_private_rider = self._user_has_rider_access(rider, restaurant_id)
        if not is_private_rider and rider.rider_work_mode not in {"freelance", "platform"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected rider is not assigned to this restaurant.",
            )
        if not is_private_rider and not rider.is_accepting_offers:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected rider is offline.",
            )

        dispatch_service = RiderDispatchService(self.session)
        offer = await dispatch_service.dispatch_manual_offer(
            order=order,
            restaurant=order.restaurant,
            rider_user_id=rider_user_id,
        )
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order, rider_offer=offer)

    async def rider_claim_order(self, rider_user_id: int, order_id: int) -> MerchantOrderResponse:
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if order.rider_user_id and order.rider_user_id != rider_user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already assigned to another rider.")

        rider = await self._load_user_with_roles(rider_user_id)
        if rider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found.")
        dispatch_service = RiderDispatchService(self.session)
        pending_offer = await dispatch_service.get_pending_offer_for_rider(
            rider_user_id=rider_user_id,
            order_id=order_id,
        )
        if pending_offer is not None:
            await dispatch_service.accept_offer(user=rider, offer_id=pending_offer.id)
            accepted_order = await self.repo.get_by_id(order_id)
            if accepted_order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
            return self._format_merchant_order_response(accepted_order)

        has_restaurant_assignment = self._user_has_rider_access(rider, order.restaurant_id)
        can_claim_open = (
            rider.rider_work_mode in {"freelance", "platform"}
            and rider.is_accepting_offers
            and order.rider_assignment_state == "open_unfilled"
            and order.restaurant is not None
            and order.restaurant.rider_dispatch_policy != "private_only"
        )
        if not has_restaurant_assignment and not can_claim_open:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This order is not available for you to claim.",
            )

        now = datetime.now(UTC)
        next_status = OrderStatus.preparing if order.status == OrderStatus.placed else order.status
        # Conditional UPDATE (compare-and-swap on rider_user_id IS NULL)
        # instead of a plain ORM attribute mutation + commit: two riders
        # calling this concurrently for the same open order must not both
        # succeed. PostgreSQL serializes concurrent UPDATEs on the same row,
        # so whichever commits first wins and the second sees rowcount == 0.
        claimed = await self.session.execute(
            update(Order)
            .where(Order.id == order_id, Order.rider_user_id.is_(None))
            .values(
                rider_user_id=rider_user_id,
                rider_assigned_at=order.rider_assigned_at or now,
                status=next_status,
                preparing_at=order.preparing_at or (now if next_status == OrderStatus.preparing else None),
                rider_assignment_state="assigned",
            )
        )
        if claimed.rowcount != 1:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This order has already been claimed by another rider.",
            )
        await self.session.commit()
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order)

    async def release_rider_assignment(
        self, rider_user_id: int, order_id: int, reason: str | None = None
    ) -> MerchantOrderResponse:
        """Lets an assigned rider back out before pickup (bike broke down,
        emergency, etc.) instead of being stuck with a job they can't
        actually deliver — there was previously no way to do this at all.
        Once the food's already been picked up it's too late to hand off
        cleanly, so that case still requires the restaurant/support."""
        order = await self.repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if order.rider_user_id != rider_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This order is not assigned to you.")
        if order.picked_up_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This order has already been picked up — contact the restaurant or support to hand it off.",
            )
        if order.status in {OrderStatus.delivered, OrderStatus.cancelled}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This order is already closed.")

        rider = await self._load_user_with_roles(rider_user_id)
        if rider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rider not found.")

        dispatch_service = RiderDispatchService(self.session)
        await dispatch_service.release_assignment(rider=rider, order=order, reason=reason)

        refreshed = await self.repo.get_by_id(order_id)
        if refreshed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(refreshed)

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
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if previous_status != OrderStatus.delivered:
            # Re-fetched fresh above (rather than session.refresh(), which
            # only refreshes column attributes) so .rider/.restaurant are
            # guaranteed loaded and not stale before computing the payout.
            try:
                await RiderPayoutService(self.session).compute_payout_for_order(order)
            except Exception:
                logging.getLogger("yummy.order").exception(
                    "Failed to compute rider payout for order %s", order.id
                )
            try:
                await RestaurantSettlementService(self.session).compute_settlement_for_order(order)
            except Exception:
                logging.getLogger("yummy.order").exception(
                    "Failed to compute restaurant settlement for order %s", order.id
                )
            order = await self.repo.get_by_id(order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        return self._format_merchant_order_response(order)

    async def _get_active_merchant_restaurant_id(self, merchant_user_id: int) -> int | None:
        from app.modules.workspaces.repository import WorkspaceRepository

        workspace_repo = WorkspaceRepository(self.session)
        restaurant_id = await workspace_repo.get_active_merchant_restaurant_id(merchant_user_id)
        if restaurant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active workspace is not a merchant workspace.",
            )
        return restaurant_id

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
            if assignment.restaurant_id is not None
            and assignment.assignment_type in {"rider_private", "private_rider"}
        }
        active_restaurant_id = user.active_restaurant_id
        all_restaurant_ids = scoped_restaurant_ids | assignment_restaurant_ids
        if restaurant_id in all_restaurant_ids:
            return True
        if active_restaurant_id == restaurant_id:
            return True
        return False
