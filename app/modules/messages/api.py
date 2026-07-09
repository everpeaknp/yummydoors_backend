from __future__ import annotations

import json
import logging
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
from app.modules.workspaces.repository import WorkspaceRepository

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
    # Broadcast to all connected merchant dashboards for this restaurant
    await manager.broadcast(
        restaurant_id,
        {"event": "new_message", "customer_id": customer_id, "message": response.model_dump()},
    )
    # Broadcast to the specific customer
    await customer_manager.broadcast(
        customer_id,
        {"event": "new_message", "restaurant_id": restaurant_id, "message": response.model_dump()},
    )
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
    # Broadcast to merchant
    await manager.broadcast(
        restaurant_id,
        {"event": "new_message", "customer_id": current_user.id, "message": response.model_dump()},
    )
    # Broadcast to customer
    await customer_manager.broadcast(
        current_user.id,
        {"event": "new_message", "restaurant_id": restaurant_id, "message": response.model_dump()},
    )
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
