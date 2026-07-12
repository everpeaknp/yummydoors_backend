from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.orders.repository import OrderRepository
from app.modules.orders.models import OrderStatus
from app.modules.realtime.bus import ORDER_CUSTOMER_CHANNEL, ORDER_MERCHANT_CHANNEL, ORDER_RIDER_CHANNEL, realtime_bus
from app.modules.rider_dispatch.schemas import (
    RiderDispatchCandidateResponse,
    RiderInvitationActionRequest,
    RiderInvitationCreateRequest,
    RiderInvitationResponse,
    RiderDispatchOfferResponse,
)
from app.modules.rider_dispatch.service import RiderDispatchService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/rider-dispatch", tags=["Rider Dispatch"])


@router.get("/restaurants/{restaurant_id}/candidates", response_model=ApiResponse[list[RiderDispatchCandidateResponse]])
async def list_candidates(
    restaurant_id: int,
    order_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderDispatchService(db)
    data = await service.list_candidates(merchant_user_id=current_user.id, restaurant_id=restaurant_id, order_id=order_id)
    return ApiResponse(message="Dispatch candidates fetched successfully.", data=data)


@router.get("/restaurants/{restaurant_id}/invitations", response_model=ApiResponse[list[RiderInvitationResponse]])
async def list_invitations(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderDispatchService(db)
    data = await service.list_invitations_for_restaurant(current_user.id, restaurant_id)
    return ApiResponse(message="Rider invitations fetched successfully.", data=data)


@router.post("/restaurants/{restaurant_id}/invitations", response_model=ApiResponse[RiderInvitationResponse])
async def invite_rider(
    restaurant_id: int,
    payload: RiderInvitationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RiderDispatchService(db)
    data = await service.invite_rider(merchant_user_id=current_user.id, restaurant_id=restaurant_id, payload=payload)
    return ApiResponse(message="Rider invitation created successfully.", data=data)


@router.post("/invitations/{invitation_id}/accept", response_model=ApiResponse[RiderInvitationResponse])
async def accept_invitation(
    invitation_id: int,
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = RiderDispatchService(db)
    data = await service.accept_invitation(user=current_user, invitation_id=invitation_id)
    return ApiResponse(message="Invitation accepted successfully.", data=data)


@router.post("/invitations/{invitation_id}/reject", response_model=ApiResponse[RiderInvitationResponse])
async def reject_invitation(
    invitation_id: int,
    payload: RiderInvitationActionRequest | None = None,
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = RiderDispatchService(db)
    data = await service.reject_invitation(user=current_user, invitation_id=invitation_id, payload=payload)
    return ApiResponse(message="Invitation rejected successfully.", data=data)


@router.post("/offers/{offer_id}/accept", response_model=ApiResponse[RiderDispatchOfferResponse])
async def accept_offer(
    offer_id: int,
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = RiderDispatchService(db)
    data = await service.accept_offer(user=current_user, offer_id=offer_id)
    order = await OrderRepository(db).get_by_id(data.order_id)
    if order is not None:
        payload = {
            "event": "order_update",
            "order_id": order.id,
            "order_number": order.order_number,
            "status": (order.status.value if isinstance(order.status, OrderStatus) else str(order.status)),
            "restaurant_id": order.restaurant_id,
            "customer_id": order.customer_id,
            "rider_user_id": current_user.id,
        }
        await realtime_bus.publish(ORDER_MERCHANT_CHANNEL, payload)
        await realtime_bus.publish(ORDER_CUSTOMER_CHANNEL, payload)
        await realtime_bus.publish(ORDER_RIDER_CHANNEL, payload)
    return ApiResponse(message="Offer accepted successfully.", data=data)


@router.post("/offers/{offer_id}/reject", response_model=ApiResponse[RiderDispatchOfferResponse])
async def reject_offer(
    offer_id: int,
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = RiderDispatchService(db)
    data = await service.reject_offer(user=current_user, offer_id=offer_id)
    return ApiResponse(message="Offer rejected successfully.", data=data)
