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
from app.modules.orders.models import OrderStatus
from app.modules.orders.schemas import OrderResponse, CheckoutRequest, OrderSummaryRequest, OrderSummaryResponse, MerchantOrderResponse
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])

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
    
    # Broadcast real-time alert to the specific merchant's dashboard
    await order_manager.broadcast_order_update(
        new_order.restaurantId,
        {
            "event": "new_order",
            "order_id": new_order.id,
            "status": "placed",
            "order_number": new_order.orderNumber,
        },
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
    # Broadcast real-time update to connected merchant dashboards
    from app.modules.workspaces.repository import WorkspaceRepository
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_active_workspace(current_user.id)
    if workspace and workspace.primary_restaurant_id:
        await order_manager.broadcast_order_update(
            workspace.primary_restaurant_id,
            {
                "event": "order_update",
                "order_id": order_id,
                "status": new_status.value,
                "order_number": updated.orderNumber,
            },
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
    if not workspace or workspace.workspace_type != "merchant" or not workspace.primary_restaurant_id:
        await websocket.close(code=4003)
        return

    restaurant_id = workspace.primary_restaurant_id
    await order_manager.connect(websocket, restaurant_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        order_manager.disconnect(websocket, restaurant_id)
