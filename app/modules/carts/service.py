from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.carts.models import Cart
from app.modules.carts.repository import CartRepository
from app.modules.carts.schemas import (
    CartAddressSummary,
    CartContextUpdate,
    CartCouponApplyRequest,
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartPricingBreakdown,
    CartResponse,
)


class CartService:
    def __init__(self, session: AsyncSession):
        self.repo = CartRepository(session)

    @staticmethod
    def _build_address_summary(cart: Cart) -> CartAddressSummary | None:
        if cart.address is None:
            return None

        parts = [
            cart.address.address_line_1,
            cart.address.area,
            cart.address.city,
        ]
        address_summary = ", ".join(part for part in parts if part) or cart.address.recipient_name
        return CartAddressSummary(
            id=cart.address.id,
            label=cart.address.label,
            recipient_name=cart.address.recipient_name,
            phone_number=cart.address.phone_number,
            address_summary=address_summary,
            latitude=cart.address.latitude,
            longitude=cart.address.longitude,
        )

    @staticmethod
    def _resolve_coupon_discount(code: str | None, items_total: float) -> float:
        if not code:
            return 0.0

        normalized = code.strip().upper()
        if normalized == "WELCOME50":
            return min(50.0, items_total)
        if normalized == "FREEDEL":
            return 0.0
        if normalized == "SAVE10":
            return round(items_total * 0.1, 2)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid coupon code.",
        )

    def _recalculate_cart_totals(self, cart: Cart) -> None:
        items_total = 0.0
        for item in cart.items:
            if item.menu_item:
                unit_price = item.menu_item.price
                modifiers = {
                    option.id: option.price_adjustment
                    for group in item.menu_item.modifier_groups
                    for option in group.items
                    if option.is_available
                }
                add_ons = {add_on.id: add_on.price for add_on in item.menu_item.add_ons if add_on.is_available}
                unit_price += sum(modifiers.get(modifier_id, 0.0) for modifier_id in item.modifier_ids)
                unit_price += sum(
                    add_ons.get(int(selection["add_on_id"]), 0.0) * int(selection.get("quantity", 1))
                    for selection in item.add_on_selections
                )
                items_total += unit_price * item.quantity

        coupon_discount = self._resolve_coupon_discount(cart.coupon_code, items_total) if cart.coupon_code else 0.0
        delivery_fee = 0.0 if cart.coupon_code and cart.coupon_code.strip().upper() == "FREEDEL" else 100.0
        service_fee = round(items_total * 0.05, 2)
        tax_amount = round(items_total * 0.13, 2)
        subtotal_amount = items_total - coupon_discount
        total_amount = max(round(subtotal_amount + delivery_fee + service_fee + tax_amount, 2), 0.0)

        cart.coupon_discount = coupon_discount
        cart.delivery_fee = delivery_fee
        cart.service_fee = service_fee
        cart.tax_amount = tax_amount
        cart.subtotal_amount = round(subtotal_amount, 2)
        cart.total_amount = total_amount

    def _format_cart_response(self, cart: Cart) -> CartResponse:
        self._recalculate_cart_totals(cart)

        items_count = 0
        formatted_items: list[CartItemResponse] = []
        items_total = 0.0

        for item in cart.items:
            if item.menu_item:
                items_count += item.quantity
                items_total += item.menu_item.price * item.quantity
                formatted_items.append(
                    CartItemResponse(
                        id=item.id,
                        menu_item_id=item.menu_item_id,
                        quantity=item.quantity,
                        name=item.menu_item.name,
                        price=item.menu_item.price,
                        image_url=item.menu_item.image_url,
                        modifier_ids=item.modifier_ids,
                        add_on_selections=item.add_on_selections,
                        modifier_selections=[],
                    )
                )

        restaurant_name = cart.restaurant.name if cart.restaurant else "Unknown Restaurant"
        restaurant_image_asset = cart.restaurant.logo_url if cart.restaurant else None
        eta_min = cart.restaurant.delivery_eta_min_minutes if cart.restaurant else 20
        eta_max = cart.restaurant.delivery_eta_max_minutes if cart.restaurant else 30
        eta_text = f"{eta_min}-{eta_max} min" if eta_min and eta_max else "20-30 min"

        return CartResponse(
            id=cart.id,
            restaurant_id=cart.restaurant_id,
            status=cart.status,
            items=formatted_items,
            items_count=items_count,
            total_price=cart.total_amount,
            restaurant_name=restaurant_name,
            restaurant_image_asset=restaurant_image_asset,
            eta_text=eta_text,
            address=self._build_address_summary(cart),
            needs_cutlery=cart.needs_cutlery,
            cooking_request=cart.cooking_request,
            delivery_instruction=cart.delivery_instruction,
            coupon_code=cart.coupon_code,
            pricing=CartPricingBreakdown(
                items_total=round(items_total, 2),
                coupon_discount=cart.coupon_discount,
                delivery_fee=cart.delivery_fee,
                service_fee=cart.service_fee,
                tax_amount=cart.tax_amount,
                subtotal_amount=cart.subtotal_amount,
                total_amount=cart.total_amount,
            ),
        )

    async def _save_and_format(self, cart: Cart) -> CartResponse:
        self._recalculate_cart_totals(cart)
        await self.repo.update_cart_context(
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
        refreshed = await self.repo.get_active_cart(cart.customer_id, cart.restaurant_id)
        if refreshed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return self._format_cart_response(refreshed)

    async def get_all_active_carts(self, customer_id: int) -> list[CartResponse]:
        carts = await self.repo.get_all_active_carts(customer_id)
        return [await self._save_and_format(cart) for cart in carts]

    async def get_active_cart(self, customer_id: int, restaurant_id: int) -> CartResponse:
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return await self._save_and_format(cart)

    async def add_item_to_cart(self, customer_id: int, restaurant_id: int, item_data: CartItemCreate) -> CartResponse:
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if not cart:
            cart = await self.repo.create_cart(customer_id, restaurant_id)

        menu_item = next((item.menu_item for item in cart.items if item.menu_item_id == item_data.menu_item_id), None)
        if menu_item is None:
            from app.modules.catalog.models import MenuItem
            from app.modules.catalog.models import MenuModifierGroup
            result = await self.repo.session.execute(
                select(MenuItem)
                .options(
                    selectinload(MenuItem.modifier_groups).selectinload(MenuModifierGroup.items),
                    selectinload(MenuItem.add_ons),
                )
                .where(MenuItem.id == item_data.menu_item_id, MenuItem.restaurant_id == restaurant_id)
            )
            menu_item = result.scalar_one_or_none()
        if menu_item is None or not menu_item.is_available:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Menu item is unavailable.")
        modifier_options = {
            option.id: option
            for group in menu_item.modifier_groups
            for option in group.items
        }
        for modifier_id in item_data.modifier_ids:
            option = modifier_options.get(modifier_id)
            if option is None or not option.is_available:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or unavailable modifier.")
        selected_modifier_ids = set(item_data.modifier_ids)
        for group in menu_item.modifier_groups:
            group_ids = {option.id for option in group.items if option.is_available}
            selected_count = len(selected_modifier_ids.intersection(group_ids))
            if group.is_required and selected_count < group.min_selections:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Modifier group '{group.name}' requires more selections.")
            if selected_count > group.max_selections:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Modifier group '{group.name}' allows at most {group.max_selections} selections.")
        add_on_options = {add_on.id: add_on for add_on in menu_item.add_ons}
        normalized_add_ons: list[dict[str, int]] = []
        for selection in item_data.add_on_selections:
            add_on = add_on_options.get(selection["add_on_id"])
            quantity = selection.get("quantity", 1)
            if add_on is None or not add_on.is_available or quantity < 1 or quantity > add_on.max_quantity:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or unavailable add-on selection.")
            normalized_add_ons.append({"add_on_id": add_on.id, "quantity": quantity})
        await self.repo.add_item(cart.id, item_data.menu_item_id, item_data.quantity, item_data.modifier_ids, normalized_add_ons)
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return await self._save_and_format(cart)

    async def update_item_quantity(self, customer_id: int, restaurant_id: int, item_id: int, update_data: CartItemUpdate) -> CartResponse:
        item = await self.repo.update_item_quantity(item_id, update_data.quantity)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return await self._save_and_format(cart)

    async def remove_item_from_cart(self, customer_id: int, restaurant_id: int, item_id: int) -> CartResponse:
        success = await self.repo.remove_item(item_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return await self._save_and_format(cart)

    async def update_cart_context(self, customer_id: int, restaurant_id: int, payload: CartContextUpdate) -> CartResponse:
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        update_data = payload.model_dump(exclude_unset=True)
        if "address_id" in update_data and update_data["address_id"] is not None:
            address = await self.repo.get_customer_address(customer_id, update_data["address_id"])
            if address is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid address.")

        await self.repo.update_cart_context(cart, update_data)
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return await self._save_and_format(cart)

    async def apply_coupon(self, customer_id: int, restaurant_id: int, payload: CartCouponApplyRequest) -> CartResponse:
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        cart.coupon_code = payload.coupon_code.strip().upper()
        return await self._save_and_format(cart)

    async def remove_coupon(self, customer_id: int, restaurant_id: int) -> CartResponse:
        cart = await self.repo.get_active_cart(customer_id, restaurant_id)
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        cart.coupon_code = None
        return await self._save_and_format(cart)
