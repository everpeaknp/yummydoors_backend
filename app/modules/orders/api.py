import logging
import json
from typing import List
from fastapi import APIRouter, Body, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.notifications.service import NotificationService
from app.modules.orders.models import OrderStatus
from app.modules.orders.schemas import OrderResponse, CheckoutRequest, OrderSummaryRequest, OrderSummaryResponse, MerchantOrderResponse
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])
logger = logging.getLogger(__name__)


def build_customer_order_event(order: OrderResponse, *, status_value: str) -> dict:
    status_copy = status_value.replace("toPay", "to pay")
    title = f"Order {status_copy}"
    body = f"{order.restaurantName} updated your order to {status_copy}."
    if status_value == "placed":
        title = "Order placed"
        body = f"{order.restaurantName} received your order."
    elif status_value == "preparing":
        title = "Order preparing"
        body = f"{order.restaurantName} started preparing your order."
    elif status_value == "delivered":
        title = "Order delivered"
        body = f"{order.restaurantName} marked your order as delivered."
    elif status_value == "cancelled":
        title = "Order cancelled"
        body = f"{order.restaurantName} cancelled your order."

    return NotificationService.build_order_notification_payload(
        audience="customer",
        event="order_update",
        order_id=order.id,
        order_number=order.orderNumber,
        status=status_value,
        restaurant_id=order.restaurantId,
        restaurant_name=order.restaurantName,
        title=title,
        body=body,
        deep_link="/orders",
    )


def build_merchant_order_event(
    *,
    order_id: int,
    order_number: str,
    restaurant_id: int | None,
    restaurant_name: str,
    customer_name: str,
    status_value: str,
    event_name: str,
) -> dict:
    if event_name == "new_order":
        title = "New order received"
        body = f"{customer_name} placed order {order_number}."
    else:
        title = f"Order {status_value}"
        body = f"Order {order_number} is now {status_value}."

    return NotificationService.build_order_notification_payload(
        audience="merchant",
        event=event_name,
        order_id=order_id,
        order_number=order_number,
        status=status_value,
        restaurant_id=restaurant_id,
        restaurant_name=restaurant_name,
        title=title,
        body=body,
        deep_link=f"/merchant/orders/{order_id}",
    )


async def safe_send_order_notifications(
    *,
    db: AsyncSession,
    customer_user_id: int | None = None,
    customer_payload: dict | None = None,
    merchant_restaurant_id: int | None = None,
    merchant_payload: dict | None = None,
) -> None:
    try:
        service = NotificationService(db)
        if customer_user_id is not None and customer_payload is not None:
            await service.send_web_push_to_user(user_id=customer_user_id, payload=customer_payload)
            await service.send_fcm_to_user(user_id=customer_user_id, payload=customer_payload)
        if merchant_restaurant_id is not None and merchant_payload is not None:
            await service.send_web_push_to_merchants(
                restaurant_id=merchant_restaurant_id,
                payload=merchant_payload,
            )
    except Exception:
        logger.exception("failed to send order web push notifications")

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
    new_order = await service.checkout_cart(current_user.id, cart_id, checkout_data)

    customer_payload = build_customer_order_event(new_order, status_value="placed")
    merchant_payload = build_merchant_order_event(
        order_id=new_order.id,
        order_number=new_order.orderNumber,
        restaurant_id=new_order.restaurantId,
        restaurant_name=new_order.restaurantName,
        customer_name=current_user.full_name or current_user.email or "A customer",
        status_value="placed",
        event_name="new_order",
    )

    try:
        await order_manager.broadcast_order_update(new_order.restaurantId, merchant_payload)
        await customer_order_manager.broadcast_order_update(current_user.id, customer_payload)
    except Exception:
        logger.exception("failed to broadcast checkout order websocket event")

    await safe_send_order_notifications(
        db=db,
        customer_user_id=current_user.id,
        customer_payload=customer_payload,
        merchant_restaurant_id=new_order.restaurantId,
        merchant_payload=merchant_payload,
    )
    return new_order


@router.get("/merchant/me", response_model=List[MerchantOrderResponse])
async def list_merchant_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    return await service.get_merchant_orders(current_user.id)


@router.patch("/merchant/{order_id}/status", response_model=MerchantOrderResponse)
async def update_merchant_order_status(
    order_id: int,
    new_status: OrderStatus,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = OrderService(db)
    updated = await service.update_merchant_order_status(current_user.id, order_id, new_status)

    customer_payload = build_customer_order_event(updated, status_value=new_status.value)
    from app.modules.workspaces.repository import WorkspaceRepository
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_active_workspace(current_user.id)
    merchant_restaurant_id = workspace.primary_restaurant_id if workspace and workspace.primary_restaurant_id else None
    merchant_payload = build_merchant_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=merchant_restaurant_id,
        restaurant_name=updated.restaurantName,
        customer_name=updated.customerName,
        status_value=new_status.value,
        event_name="order_update",
    )
    try:
        if merchant_restaurant_id:
            await order_manager.broadcast_order_update(
                merchant_restaurant_id,
                merchant_payload,
            )
        await customer_order_manager.broadcast_order_update(updated.customerId, customer_payload)
    except Exception:
        logger.exception("failed to broadcast merchant order websocket event")

    await safe_send_order_notifications(
        db=db,
        customer_user_id=updated.customerId,
        customer_payload=customer_payload,
        merchant_restaurant_id=merchant_restaurant_id,
        merchant_payload=merchant_payload,
    )
    return updated


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket connection manager for order tracking
# ──────────────────────────────────────────────────────────────────────────────

class OrderConnectionManager:
    def __init__(self):
        # restaurant_id -> list[WebSocket]
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, restaurant_id: int):
        await ws.accept()
        self._connections.setdefault(restaurant_id, []).append(ws)

    def disconnect(self, ws: WebSocket, restaurant_id: int):
        conns = self._connections.get(restaurant_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast_order_update(self, restaurant_id: int, payload: dict):
        for ws in list(self._connections.get(restaurant_id, [])):
            try:
                await ws.send_text(json.dumps(payload, default=str))
            except Exception:
                pass


order_manager = OrderConnectionManager()
customer_order_manager = OrderConnectionManager()


@router.websocket("/ws/merchant")
async def ws_merchant_orders(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket for real-time merchant order tracking.
    Connect with:  ws://host/api/v1/orders/ws/merchant?token=<JWT>
    The server pushes { event: 'order_update', order_id, status, updated_at } whenever
    update_merchant_order_status is called.
    """
    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4001)
        return

    auth_repo = AuthRepository(db)
    auth_service = AuthService(auth_repo)
    user = await auth_service.get_current_user(user_id)
    if user is None:
        await websocket.close(code=4001)
        return

    restaurant_id = None
    from app.modules.workspaces.repository import WorkspaceRepository
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_active_workspace(user_id)
    if workspace and workspace.workspace_type == "merchant" and workspace.primary_restaurant_id:
        restaurant_id = workspace.primary_restaurant_id
    else:
        token_restaurant_id = payload.get("restaurant_id")
        if isinstance(token_restaurant_id, int) and token_restaurant_id > 0:
            restaurant_id = token_restaurant_id

    if not restaurant_id:
        logger.warning(
            "merchant websocket rejected user_id=%s active_workspace=%s token_restaurant_id=%s",
            user_id,
            getattr(workspace, "workspace_type", None),
            payload.get("restaurant_id"),
        )
        await websocket.close(code=4003)
        return

    await order_manager.connect(websocket, restaurant_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        order_manager.disconnect(websocket, restaurant_id)


@router.websocket("/ws/customer")
async def ws_customer_orders(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket for customer order tracking.
    Connect with:  ws://host/api/v1/orders/ws/customer?token=<JWT>
    """
    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4001)
        return

    auth_repo = AuthRepository(db)
    auth_service = AuthService(auth_repo)
    user = await auth_service.get_current_user(user_id)
    if user is None:
        await websocket.close(code=4001)
        return

    await customer_order_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        customer_order_manager.disconnect(websocket, user_id)
