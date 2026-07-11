import logging
import json
from typing import List
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.notifications.service import NotificationService
from app.modules.realtime.bus import (
    ORDER_CUSTOMER_CHANNEL,
    ORDER_MERCHANT_CHANNEL,
    ORDER_RIDER_CHANNEL,
    realtime_bus,
)
from app.tasks.notifications import send_merchant_push_task, send_user_push_task
from app.modules.orders.models import OrderStatus
from app.modules.orders.schemas import (
    CheckoutRequest,
    MerchantOrderResponse,
    OrderResponse,
    OrderSummaryRequest,
    OrderSummaryResponse,
    RiderAssignmentRequest,
    RiderSummaryResponse,
)
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
    elif status_value == "rider_assigned":
        title = "Rider assigned"
        body = f"A rider has been assigned to your order from {order.restaurantName}."
    elif status_value == "picked_up":
        title = "Order picked up"
        body = f"Your rider picked up the order from {order.restaurantName}."
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


def build_rider_order_event(
    *,
    order_id: int,
    order_number: str,
    restaurant_id: int | None,
    restaurant_name: str,
    status_value: str,
    event_name: str,
) -> dict:
    if event_name == "rider_assigned":
        title = "New rider job"
        body = f"Order {order_number} was assigned to you."
    elif event_name == "picked_up":
        title = "Pickup complete"
        body = f"Order {order_number} was marked picked up."
    elif event_name == "delivered":
        title = "Delivery completed"
        body = f"Order {order_number} was marked delivered."
    else:
        title = f"Order {status_value}"
        body = f"Order {order_number} changed to {status_value}."

    return NotificationService.build_order_notification_payload(
        audience="rider",
        event=event_name,
        order_id=order_id,
        order_number=order_number,
        status=status_value,
        restaurant_id=restaurant_id,
        restaurant_name=restaurant_name,
        title=title,
        body=body,
        deep_link=f"/rider/orders/{order_id}",
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
    rider_user_id: int | None = None,
    rider_payload: dict | None = None,
) -> None:
    try:
        service = NotificationService(db)
        if customer_user_id is not None and customer_payload is not None:
            await service.create_notification_from_payload(
                recipient_user_id=customer_user_id,
                payload=customer_payload,
                actor_user_id=customer_payload.get("actor_user_id"),
            )
            try:
                send_user_push_task.delay(user_id=customer_user_id, payload=customer_payload)
            except Exception:
                await service.send_web_push_to_user(user_id=customer_user_id, payload=customer_payload)
                await service.send_fcm_to_user(user_id=customer_user_id, payload=customer_payload)
        if merchant_restaurant_id is not None and merchant_payload is not None:
            await service.create_merchant_notifications_from_payload(
                restaurant_id=merchant_restaurant_id,
                payload=merchant_payload,
                actor_user_id=merchant_payload.get("actor_user_id"),
                order_id=merchant_payload.get("order_id"),
            )
            try:
                send_merchant_push_task.delay(restaurant_id=merchant_restaurant_id, payload=merchant_payload)
            except Exception:
                await service.send_web_push_to_merchants(
                    restaurant_id=merchant_restaurant_id,
                    payload=merchant_payload,
                )
                await service.send_fcm_to_merchants(
                    restaurant_id=merchant_restaurant_id,
                    payload=merchant_payload,
                )
        if rider_user_id is not None and rider_payload is not None:
            await service.create_notification_from_payload(
                recipient_user_id=rider_user_id,
                payload=rider_payload,
                actor_user_id=rider_payload.get("actor_user_id"),
            )
            try:
                send_user_push_task.delay(user_id=rider_user_id, payload=rider_payload)
            except Exception:
                await service.send_web_push_to_user(user_id=rider_user_id, payload=rider_payload)
                await service.send_fcm_to_user(user_id=rider_user_id, payload=rider_payload)
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
        await realtime_bus.publish(ORDER_MERCHANT_CHANNEL, _with_restaurant_scope(merchant_payload, new_order.restaurantId))
        await realtime_bus.publish(ORDER_CUSTOMER_CHANNEL, _with_customer_scope(customer_payload, current_user.id))
    except Exception:
        logger.exception("failed to publish checkout order websocket event")

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


@router.get("/merchant/riders", response_model=List[RiderSummaryResponse])
async def list_merchant_riders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    return await service.list_restaurant_riders(current_user.id)


@router.post("/merchant/{order_id}/assign-rider", response_model=MerchantOrderResponse)
async def assign_rider_to_order(
    order_id: int,
    payload: RiderAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    updated = await service.assign_rider_to_order(current_user.id, order_id, payload.rider_user_id)

    customer_payload = build_customer_order_event(updated, status_value="rider_assigned")
    merchant_payload = build_merchant_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=updated.restaurantId,
        restaurant_name=updated.restaurantName,
        customer_name=updated.customerName,
        status_value="rider_assigned",
        event_name="order_update",
    )
    rider_payload = build_rider_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=updated.restaurantId,
        restaurant_name=updated.restaurantName,
        status_value="rider_assigned",
        event_name="rider_assigned",
    )
    try:
        await realtime_bus.publish(ORDER_MERCHANT_CHANNEL, _with_restaurant_scope(merchant_payload, updated.restaurantId))
        await realtime_bus.publish(ORDER_CUSTOMER_CHANNEL, _with_customer_scope(customer_payload, updated.customerId))
        await realtime_bus.publish(ORDER_RIDER_CHANNEL, _with_rider_scope(rider_payload, payload.rider_user_id))
    except Exception:
        logger.exception("failed to publish rider assignment websocket event")

    await safe_send_order_notifications(
        db=db,
        customer_user_id=updated.customerId,
        customer_payload=customer_payload,
        merchant_restaurant_id=updated.restaurantId,
        merchant_payload=merchant_payload,
        rider_user_id=payload.rider_user_id,
        rider_payload=rider_payload,
    )
    return updated


@router.get("/rider/me", response_model=List[MerchantOrderResponse])
async def list_rider_orders(
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    return await service.get_rider_orders(current_user.id)


@router.post("/rider/{order_id}/claim", response_model=MerchantOrderResponse)
async def claim_rider_order(
    order_id: int,
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    updated = await service.rider_claim_order(current_user.id, order_id)

    customer_payload = build_customer_order_event(updated, status_value="rider_assigned")
    merchant_payload = build_merchant_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=updated.restaurantId,
        restaurant_name=updated.restaurantName,
        customer_name=updated.customerName,
        status_value="rider_assigned",
        event_name="order_update",
    )
    rider_payload = build_rider_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=updated.restaurantId,
        restaurant_name=updated.restaurantName,
        status_value="rider_assigned",
        event_name="rider_assigned",
    )
    try:
        await realtime_bus.publish(ORDER_MERCHANT_CHANNEL, _with_restaurant_scope(merchant_payload, updated.restaurantId))
        await realtime_bus.publish(ORDER_CUSTOMER_CHANNEL, _with_customer_scope(customer_payload, updated.customerId))
        await realtime_bus.publish(ORDER_RIDER_CHANNEL, _with_rider_scope(rider_payload, current_user.id))
    except Exception:
        logger.exception("failed to publish rider claim websocket event")

    await safe_send_order_notifications(
        db=db,
        customer_user_id=updated.customerId,
        customer_payload=customer_payload,
        merchant_restaurant_id=updated.restaurantId,
        merchant_payload=merchant_payload,
        rider_user_id=current_user.id,
        rider_payload=rider_payload,
    )
    return updated


@router.patch("/rider/{order_id}/picked-up", response_model=MerchantOrderResponse)
async def mark_rider_picked_up(
    order_id: int,
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    updated = await service.rider_mark_picked_up(current_user.id, order_id)

    customer_payload = build_customer_order_event(updated, status_value="picked_up")
    merchant_payload = build_merchant_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=updated.restaurantId,
        restaurant_name=updated.restaurantName,
        customer_name=updated.customerName,
        status_value="picked_up",
        event_name="order_update",
    )
    rider_payload = build_rider_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=updated.restaurantId,
        restaurant_name=updated.restaurantName,
        status_value="picked_up",
        event_name="picked_up",
    )
    try:
        await realtime_bus.publish(ORDER_MERCHANT_CHANNEL, _with_restaurant_scope(merchant_payload, updated.restaurantId))
        await realtime_bus.publish(ORDER_CUSTOMER_CHANNEL, _with_customer_scope(customer_payload, updated.customerId))
        await realtime_bus.publish(ORDER_RIDER_CHANNEL, _with_rider_scope(rider_payload, current_user.id))
    except Exception:
        logger.exception("failed to publish rider pickup websocket event")

    await safe_send_order_notifications(
        db=db,
        customer_user_id=updated.customerId,
        customer_payload=customer_payload,
        merchant_restaurant_id=updated.restaurantId,
        merchant_payload=merchant_payload,
        rider_user_id=current_user.id,
        rider_payload=rider_payload,
    )
    return updated


@router.patch("/rider/{order_id}/delivered", response_model=MerchantOrderResponse)
async def mark_rider_delivered(
    order_id: int,
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    updated = await service.rider_mark_delivered(current_user.id, order_id)

    customer_payload = build_customer_order_event(updated, status_value="delivered")
    merchant_payload = build_merchant_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=updated.restaurantId,
        restaurant_name=updated.restaurantName,
        customer_name=updated.customerName,
        status_value="delivered",
        event_name="order_update",
    )
    rider_payload = build_rider_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=updated.restaurantId,
        restaurant_name=updated.restaurantName,
        status_value="delivered",
        event_name="delivered",
    )
    try:
        await realtime_bus.publish(ORDER_MERCHANT_CHANNEL, _with_restaurant_scope(merchant_payload, updated.restaurantId))
        await realtime_bus.publish(ORDER_CUSTOMER_CHANNEL, _with_customer_scope(customer_payload, updated.customerId))
        await realtime_bus.publish(ORDER_RIDER_CHANNEL, _with_rider_scope(rider_payload, current_user.id))
    except Exception:
        logger.exception("failed to publish rider delivered websocket event")

    await safe_send_order_notifications(
        db=db,
        customer_user_id=updated.customerId,
        customer_payload=customer_payload,
        merchant_restaurant_id=updated.restaurantId,
        merchant_payload=merchant_payload,
        rider_user_id=current_user.id,
        rider_payload=rider_payload,
    )
    return updated


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
    merchant_restaurant_id = updated.restaurantId
    merchant_payload = build_merchant_order_event(
        order_id=updated.id,
        order_number=updated.orderNumber,
        restaurant_id=merchant_restaurant_id,
        restaurant_name=updated.restaurantName,
        customer_name=updated.customerName,
        status_value=new_status.value,
        event_name="order_update",
    )
    rider_payload = None
    rider_user_id = updated.rider.id if updated.rider else None
    if rider_user_id is not None:
        rider_payload = build_rider_order_event(
            order_id=updated.id,
            order_number=updated.orderNumber,
            restaurant_id=merchant_restaurant_id,
            restaurant_name=updated.restaurantName,
            status_value=new_status.value,
            event_name="order_update",
        )
    try:
        if merchant_restaurant_id:
            await realtime_bus.publish(
                ORDER_MERCHANT_CHANNEL,
                _with_restaurant_scope(merchant_payload, merchant_restaurant_id),
            )
        await realtime_bus.publish(
            ORDER_CUSTOMER_CHANNEL,
            _with_customer_scope(customer_payload, updated.customerId),
        )
        if rider_user_id is not None and rider_payload is not None:
            await realtime_bus.publish(
                ORDER_RIDER_CHANNEL,
                _with_rider_scope(rider_payload, rider_user_id),
            )
    except Exception:
        logger.exception("failed to publish merchant order websocket event")

    await safe_send_order_notifications(
        db=db,
        customer_user_id=updated.customerId,
        customer_payload=customer_payload,
        merchant_restaurant_id=merchant_restaurant_id,
        merchant_payload=merchant_payload,
        rider_user_id=rider_user_id,
        rider_payload=rider_payload,
    )
    return updated


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket connection manager for order tracking
# ──────────────────────────────────────────────────────────────────────────────

class OrderConnectionManager:
    def __init__(self):
        # scope_id (restaurant_id or user_id) -> list[WebSocket]
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
rider_order_manager = OrderConnectionManager()


async def _broadcast_merchant_order(payload: dict) -> None:
    restaurant_id = payload.get("restaurant_id")
    if isinstance(restaurant_id, int) and restaurant_id > 0:
        await order_manager.broadcast_order_update(restaurant_id, payload)


async def _broadcast_customer_order(payload: dict) -> None:
    customer_id = payload.get("customer_id")
    if isinstance(customer_id, int) and customer_id > 0:
        await customer_order_manager.broadcast_order_update(customer_id, payload)


async def _broadcast_rider_order(payload: dict) -> None:
    rider_id = payload.get("rider_user_id")
    if isinstance(rider_id, int) and rider_id > 0:
        await rider_order_manager.broadcast_order_update(rider_id, payload)


realtime_bus.register_handler(ORDER_MERCHANT_CHANNEL, _broadcast_merchant_order)
realtime_bus.register_handler(ORDER_CUSTOMER_CHANNEL, _broadcast_customer_order)
realtime_bus.register_handler(ORDER_RIDER_CHANNEL, _broadcast_rider_order)


def _with_restaurant_scope(payload: dict, restaurant_id: int | None) -> dict:
    next_payload = dict(payload)
    if restaurant_id is not None:
        next_payload["restaurant_id"] = restaurant_id
    return next_payload


def _with_customer_scope(payload: dict, customer_id: int | None) -> dict:
    next_payload = dict(payload)
    if customer_id is not None:
        next_payload["customer_id"] = customer_id
    return next_payload


def _with_rider_scope(payload: dict, rider_user_id: int | None) -> dict:
    next_payload = dict(payload)
    if rider_user_id is not None:
        next_payload["rider_user_id"] = rider_user_id
    return next_payload


def _resolve_merchant_restaurant_id_from_claims(
    *,
    payload: dict,
    workspace,
    user,
) -> int | None:
    if workspace and workspace.workspace_type == "merchant" and workspace.primary_restaurant_id:
        return workspace.primary_restaurant_id

    token_restaurant_id = payload.get("restaurant_id")
    if isinstance(token_restaurant_id, int) and token_restaurant_id > 0:
        return token_restaurant_id

    token_restaurant_ids = payload.get("restaurant_ids")
    if isinstance(token_restaurant_ids, list):
        for item in token_restaurant_ids:
            if isinstance(item, int) and item > 0:
                return item
            if isinstance(item, str) and item.isdigit():
                return int(item)

    active_restaurant_id = getattr(user, "active_restaurant_id", None)
    if isinstance(active_restaurant_id, int) and active_restaurant_id > 0:
        return active_restaurant_id

    return None


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

    from app.modules.workspaces.repository import WorkspaceRepository
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_active_workspace(user_id)
    restaurant_id = _resolve_merchant_restaurant_id_from_claims(
        payload=payload,
        workspace=workspace,
        user=user,
    )

    if not restaurant_id:
        logger.warning(
            "merchant websocket rejected user_id=%s active_workspace=%s token_restaurant_id=%s",
            user_id,
            getattr(workspace, "workspace_type", None),
            payload.get("restaurant_id") or payload.get("restaurant_ids"),
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


@router.websocket("/ws/rider")
async def ws_rider_orders(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket for rider order tracking.
    Connect with: ws://host/api/v1/orders/ws/rider?token=<JWT>
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

    user_role_codes = {item.role.code for item in user.roles}
    if not user_role_codes.intersection({"rider"}):
        await websocket.close(code=4003)
        return

    await rider_order_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        rider_order_manager.disconnect(websocket, user_id)
