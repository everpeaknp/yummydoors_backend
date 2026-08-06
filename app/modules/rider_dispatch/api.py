from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.orders.api import (
    _with_customer_scope,
    _with_restaurant_scope,
    _with_rider_scope,
    build_customer_order_event,
    build_merchant_order_event,
    build_rider_order_event,
    safe_send_order_notifications,
)
from app.modules.orders.repository import OrderRepository
from app.modules.orders.service import OrderService
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
logger = logging.getLogger(__name__)


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

@router.post("/restaurants/{restaurant_id}/invitations/{invitation_id}/resend", response_model=ApiResponse[RiderInvitationResponse])
async def resend_invitation(restaurant_id: int, invitation_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await RiderDispatchService(db).resend_invitation(merchant_user_id=current_user.id, restaurant_id=restaurant_id, invitation_id=invitation_id)
    return ApiResponse(message="Rider invitation resent successfully.", data=data)

@router.post("/restaurants/{restaurant_id}/invitations/{invitation_id}/cancel", response_model=ApiResponse[RiderInvitationResponse])
async def cancel_invitation(restaurant_id: int, invitation_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await RiderDispatchService(db).cancel_invitation(merchant_user_id=current_user.id, restaurant_id=restaurant_id, invitation_id=invitation_id)
    return ApiResponse(message="Rider invitation cancelled successfully.", data=data)

@router.delete("/restaurants/{restaurant_id}/riders/{rider_user_id}", response_model=ApiResponse[None])
async def remove_rider(restaurant_id: int, rider_user_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await RiderDispatchService(db).remove_rider(merchant_user_id=current_user.id, restaurant_id=restaurant_id, rider_user_id=rider_user_id)
    return ApiResponse(message="Rider removed from restaurant team.", data=None)


@router.get("/invitations/me", response_model=ApiResponse[list[RiderInvitationResponse]])
async def list_my_invitations(
    current_user: User = Depends(require_role(["rider"])),
    db: AsyncSession = Depends(get_db),
):
    service = RiderDispatchService(db)
    data = await service.list_invitations_for_rider(user=current_user)
    return ApiResponse(message="Rider invitations fetched successfully.", data=data)


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
        order_service = OrderService(db)
        updated = order_service._format_merchant_order_response(order)

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
            logger.exception("failed to publish rider offer acceptance websocket event")

        await safe_send_order_notifications(
            db=db,
            customer_user_id=updated.customerId,
            customer_payload=customer_payload,
            merchant_restaurant_id=updated.restaurantId,
            merchant_payload=merchant_payload,
            rider_user_id=current_user.id,
            rider_payload=rider_payload,
        )
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
