from __future__ import annotations

import json
import logging
from urllib.parse import quote_plus
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import ConversationSummary, MessageCreate, MessageResponse
from app.modules.realtime.bus import (
    MESSAGE_CUSTOMER_CHANNEL,
    MESSAGE_MERCHANT_CHANNEL,
    realtime_bus,
)
from app.modules.notifications.service import NotificationService
from app.modules.workspaces.repository import WorkspaceRepository
from app.tasks.notifications import send_merchant_push_task, send_user_push_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/messages", tags=["Messages"])

# ──────────────────────────────────────────────────────────────────────────────
# WebSocket connection manager
# ──────────────────────────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        # restaurant_id -> list of WebSocket connections
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, restaurant_id: int):
        await ws.accept()
        self._connections.setdefault(restaurant_id, []).append(ws)

    def disconnect(self, ws: WebSocket, restaurant_id: int):
        connections = self._connections.get(restaurant_id, [])
        if ws in connections:
            connections.remove(ws)

    async def broadcast(self, restaurant_id: int, payload: dict):
        for ws in list(self._connections.get(restaurant_id, [])):
            try:
                await ws.send_text(json.dumps(payload, default=str))
            except Exception:
                pass


manager = ConnectionManager()
customer_manager = ConnectionManager()


async def _broadcast_merchant_message(payload: dict) -> None:
    restaurant_id = payload.get("restaurant_id")
    if isinstance(restaurant_id, int) and restaurant_id > 0:
        await manager.broadcast(restaurant_id, payload)


async def _broadcast_customer_message(payload: dict) -> None:
    customer_id = payload.get("customer_id")
    if isinstance(customer_id, int) and customer_id > 0:
        await customer_manager.broadcast(customer_id, payload)


realtime_bus.register_handler(MESSAGE_MERCHANT_CHANNEL, _broadcast_merchant_message)
realtime_bus.register_handler(MESSAGE_CUSTOMER_CHANNEL, _broadcast_customer_message)


def _truncate_message_preview(content: str, limit: int = 96) -> str:
    text = content.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


# ──────────────────────────────────────────────────────────────────────────────
# Helper – get active merchant restaurant_id
# ──────────────────────────────────────────────────────────────────────────────

async def _get_merchant_restaurant_id(user_id: int, session: AsyncSession) -> int:
    workspace_repo = WorkspaceRepository(session)
    workspace = await workspace_repo.get_active_workspace(user_id)
    if not workspace or workspace.workspace_type != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active workspace is not a merchant workspace.",
        )
    if not workspace.primary_restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active restaurant in this workspace.",
        )
    return workspace.primary_restaurant_id


# ──────────────────────────────────────────────────────────────────────────────
# REST endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/merchant/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
    repo = MessageRepository(db)
    messages = await repo.list_conversations(restaurant_id)

    results: list[ConversationSummary] = []
    for msg in messages:
        unread = await repo.get_unread_count(restaurant_id, msg.customer_user_id)
        results.append(
            ConversationSummary(
                customer_id=msg.customer_user_id,
                customer_name=msg.customer.full_name if msg.customer else "Unknown",
                customer_avatar=getattr(msg.customer, "avatar_url", None),
                last_message=msg.content,
                last_message_at=msg.created_at,
                unread_count=unread,
            )
        )
    return results


@router.get("/merchant/{customer_id}", response_model=list[MessageResponse])
async def get_conversation(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
    repo = MessageRepository(db)
    # Mark incoming customer messages as read
    await repo.mark_conversation_read(restaurant_id, customer_id)
    messages = await repo.get_conversation(restaurant_id, customer_id)

    return [
        MessageResponse(
            id=m.id,
            content=m.content,
            is_from_merchant=m.is_from_merchant,
            sender_name=m.sender.full_name if m.sender else "Unknown",
            created_at=m.created_at,
            read_at=m.read_at,
        )
        for m in messages
    ]


@router.post("/merchant/{customer_id}", response_model=MessageResponse)
async def send_message(
    customer_id: int,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
    repo = MessageRepository(db)
    msg = await repo.create_message(
        sender_user_id=current_user.id,
        restaurant_id=restaurant_id,
        customer_user_id=customer_id,
        content=payload.content,
        is_from_merchant=True,
    )
    response = MessageResponse(
        id=msg.id,
        content=msg.content,
        is_from_merchant=msg.is_from_merchant,
        sender_name=msg.sender.full_name if msg.sender else "Merchant",
        created_at=msg.created_at,
        read_at=msg.read_at,
    )
    merchant_event = {
        "event": "new_message",
        "customer_id": customer_id,
        "restaurant_id": restaurant_id,
        "message": response.model_dump(mode="json"),
    }
    customer_event = {
        "event": "new_message",
        "restaurant_id": restaurant_id,
        "customer_id": customer_id,
        "message": response.model_dump(mode="json"),
    }

    try:
        await realtime_bus.publish(MESSAGE_MERCHANT_CHANNEL, merchant_event)
        await realtime_bus.publish(MESSAGE_CUSTOMER_CHANNEL, customer_event)
    except Exception:
        logger.exception("failed to publish merchant message realtime event")

    try:
        restaurant_name = msg.restaurant.name if msg.restaurant else "Your restaurant"
        customer_payload = NotificationService.build_message_notification_payload(
            audience="customer",
            message_id=msg.id,
            restaurant_id=restaurant_id,
            restaurant_name=restaurant_name,
            customer_id=customer_id,
            customer_name=msg.customer.full_name if getattr(msg, "customer", None) else "Customer",
            sender_name=current_user.full_name or "Merchant",
            is_from_merchant=True,
            title=f"New message from {current_user.full_name or restaurant_name}",
            body=_truncate_message_preview(msg.content),
            deep_link=(
                f"/messages?restaurant_id={restaurant_id}"
                f"&restaurant_name={quote_plus(restaurant_name)}"
            ),
        )
        service = NotificationService(db)
        await service.create_notification_from_payload(
            recipient_user_id=customer_id,
            payload=customer_payload,
            restaurant_id=restaurant_id,
            message_id=msg.id,
            actor_user_id=current_user.id,
        )
        try:
            send_user_push_task.delay(user_id=customer_id, payload=customer_payload)
        except Exception:
            await service.send_web_push_to_user(user_id=customer_id, payload=customer_payload)
            await service.send_fcm_to_user(user_id=customer_id, payload=customer_payload)
    except Exception:
        logger.exception("failed to send customer message web push notifications")
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Customer REST endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/customer/conversations", response_model=list[ConversationSummary])
async def list_customer_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = MessageRepository(db)
    messages = await repo.list_customer_conversations(current_user.id)

    results: list[ConversationSummary] = []
    for msg in messages:
        unread = await repo.get_unread_count_for_customer(current_user.id, msg.restaurant_id)
        results.append(
            ConversationSummary(
                customer_id=msg.restaurant_id, # Reusing schema, customer_id acts as partner id (restaurant_id here)
                customer_name=msg.restaurant.name if msg.restaurant else "Unknown Restaurant",
                customer_avatar=getattr(msg.restaurant, "logo_url", None),
                last_message=msg.content,
                last_message_at=msg.created_at,
                unread_count=unread,
            )
        )
    return results


@router.get("/customer/{restaurant_id}", response_model=list[MessageResponse])
async def get_customer_conversation(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = MessageRepository(db)
    await repo.mark_customer_conversation_read(current_user.id, restaurant_id)
    messages = await repo.get_conversation(restaurant_id, current_user.id)

    return [
        MessageResponse(
            id=m.id,
            content=m.content,
            is_from_merchant=m.is_from_merchant,
            sender_name=m.sender.full_name if m.sender else "Unknown",
            created_at=m.created_at,
            read_at=m.read_at,
        )
        for m in messages
    ]


@router.post("/customer/{restaurant_id}", response_model=MessageResponse)
async def customer_send_message(
    restaurant_id: int,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = MessageRepository(db)
    msg = await repo.create_message(
        sender_user_id=current_user.id,
        restaurant_id=restaurant_id,
        customer_user_id=current_user.id,
        content=payload.content,
        is_from_merchant=False,
    )
    response = MessageResponse(
        id=msg.id,
        content=msg.content,
        is_from_merchant=msg.is_from_merchant,
        sender_name=msg.sender.full_name if msg.sender else "Customer",
        created_at=msg.created_at,
        read_at=msg.read_at,
    )
    merchant_event = {
        "event": "new_message",
        "customer_id": current_user.id,
        "restaurant_id": restaurant_id,
        "message": response.model_dump(mode="json"),
    }
    customer_event = {
        "event": "new_message",
        "restaurant_id": restaurant_id,
        "customer_id": current_user.id,
        "message": response.model_dump(mode="json"),
    }

    try:
        await realtime_bus.publish(MESSAGE_MERCHANT_CHANNEL, merchant_event)
        await realtime_bus.publish(MESSAGE_CUSTOMER_CHANNEL, customer_event)
    except Exception:
        logger.exception("failed to publish customer message realtime event")

    try:
        restaurant_name = msg.restaurant.name if msg.restaurant else "A restaurant"
        merchant_payload = NotificationService.build_message_notification_payload(
            audience="merchant",
            message_id=msg.id,
            restaurant_id=restaurant_id,
            restaurant_name=restaurant_name,
            customer_id=current_user.id,
            customer_name=current_user.full_name or current_user.email or "Customer",
            sender_name=restaurant_name,
            is_from_merchant=False,
            title=f"New message from {current_user.full_name or current_user.email or 'Customer'}",
            body=_truncate_message_preview(msg.content),
            deep_link=(
                f"/merchant/messages?customer_id={current_user.id}"
                f"&customer_name={quote_plus(current_user.full_name or current_user.email or 'Customer')}"
            ),
        )
        service = NotificationService(db)
        await service.create_merchant_notifications_from_payload(
            restaurant_id=restaurant_id,
            payload=merchant_payload,
            message_id=msg.id,
            actor_user_id=current_user.id,
        )
        try:
            send_merchant_push_task.delay(restaurant_id=restaurant_id, payload=merchant_payload)
        except Exception:
            await service.send_web_push_to_merchants(restaurant_id=restaurant_id, payload=merchant_payload)
            await service.send_fcm_to_merchants(restaurant_id=restaurant_id, payload=merchant_payload)
    except Exception:
        logger.exception("failed to send merchant message web push notifications")
    return response


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/merchant")
async def ws_merchant_messages(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket for merchant message inbox.
    Connect with:  ws://host/api/v1/messages/ws/merchant?token=<JWT>
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

    try:
        restaurant_id = await _get_merchant_restaurant_id(user_id, db)
    except HTTPException:
        await websocket.close(code=4003)
        return

    await manager.connect(websocket, restaurant_id)
    try:
        while True:
            # Keep connection alive; server pushes events via `broadcast`
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id)
@router.websocket("/ws/customer")
async def ws_customer_messages(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket for customer message inbox.
    Connect with:  ws://host/api/v1/messages/ws/customer?token=<JWT>
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

    await customer_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        customer_manager.disconnect(websocket, user_id)
