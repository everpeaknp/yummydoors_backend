from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import Role, User, UserRole
from app.modules.notifications.service import NotificationService
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import RiderSummaryResponse
from app.modules.rider_dispatch.models import OrderDispatchOffer, RestaurantRiderInvitation
from app.modules.rider_dispatch.schemas import (
    RiderDispatchCandidateResponse,
    RiderInvitationActionRequest,
    RiderInvitationCreateRequest,
    RiderInvitationResponse,
    RiderDispatchOfferResponse,
)
from app.modules.restaurants.models import Restaurant, RestaurantUserAssignment
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.realtime.bus import ORDER_RIDER_CHANNEL, realtime_bus


class RiderDispatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.notifications = NotificationService(session)

    async def invite_rider(
        self,
        *,
        merchant_user_id: int,
        restaurant_id: int,
        payload: RiderInvitationCreateRequest,
    ) -> RiderInvitationResponse:
        restaurant = await self._require_managed_restaurant(merchant_user_id, restaurant_id)
        invited_user = await self._get_user_by_email(payload.invited_email.strip().lower())

        invitation = RestaurantRiderInvitation(
            restaurant_id=restaurant.id,
            inviter_user_id=merchant_user_id,
            invited_user_id=invited_user.id if invited_user else None,
            invited_email=payload.invited_email.strip().lower(),
            invitation_type=payload.invitation_type,
            status="pending",
            notes=payload.notes.strip() if payload.notes else None,
        )
        self.session.add(invitation)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(invitation)
        return self._build_invitation_response(invitation)

    async def list_invitations_for_restaurant(self, merchant_user_id: int, restaurant_id: int) -> list[RiderInvitationResponse]:
        await self._require_managed_restaurant(merchant_user_id, restaurant_id)
        result = await self.session.execute(
            select(RestaurantRiderInvitation)
            .where(RestaurantRiderInvitation.restaurant_id == restaurant_id)
            .order_by(RestaurantRiderInvitation.created_at.desc())
        )
        return [self._build_invitation_response(item) for item in result.scalars().all()]

    async def accept_invitation(self, *, user: User, invitation_id: int) -> RiderInvitationResponse:
        invitation = await self.session.get(RestaurantRiderInvitation, invitation_id)
        if invitation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
        if invitation.status == "accepted":
            return self._build_invitation_response(invitation)
        if invitation.status not in {"pending", "sent"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation can no longer be accepted.")
        if invitation.invited_user_id is not None and invitation.invited_user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This invitation is not for your account.")
        if invitation.invited_user_id is None and invitation.invited_email.lower() != (user.email or "").lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This invitation is not for your account.")

        assignment_type = "rider_private" if invitation.invitation_type == "private" else "rider_preferred"
        existing_assignment = await self.session.execute(
            select(RestaurantUserAssignment).where(
                RestaurantUserAssignment.user_id == user.id,
                RestaurantUserAssignment.restaurant_id == invitation.restaurant_id,
                RestaurantUserAssignment.assignment_type == assignment_type,
            )
        )
        if existing_assignment.scalar_one_or_none() is None:
            self.session.add(
                RestaurantUserAssignment(
                    user_id=user.id,
                    restaurant_id=invitation.restaurant_id,
                    branch_id=None,
                    assignment_type=assignment_type,
                    source_system="yummydoors",
                    external_role_snapshot="rider_invitation",
                )
            )

        invitation.status = "accepted"
        invitation.invited_user_id = user.id
        invitation.responded_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(invitation)
        return self._build_invitation_response(invitation)

    async def reject_invitation(self, *, user: User, invitation_id: int, payload: RiderInvitationActionRequest | None = None) -> RiderInvitationResponse:
        invitation = await self.session.get(RestaurantRiderInvitation, invitation_id)
        if invitation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
        if invitation.invited_user_id is not None and invitation.invited_user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This invitation is not for your account.")
        invitation.status = "rejected"
        invitation.notes = payload.notes.strip() if payload and payload.notes else invitation.notes
        invitation.responded_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(invitation)
        return self._build_invitation_response(invitation)

    async def list_candidates(
        self,
        *,
        merchant_user_id: int,
        restaurant_id: int,
        order_id: int | None = None,
    ) -> list[RiderDispatchCandidateResponse]:
        restaurant = await self._require_managed_restaurant(merchant_user_id, restaurant_id)
        order = await self.order_repo.get_by_id(order_id) if order_id is not None else None
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role),
                selectinload(User.restaurant_assignments),
            )
            .where(User.is_active.is_(True))
        )
        users = result.scalars().unique().all()
        candidates: list[RiderDispatchCandidateResponse] = []
        for user in users:
            if not self._user_is_rider(user):
                continue
            candidate = self._build_candidate(user, restaurant, order)
            if candidate is not None:
                candidates.append(candidate)
        return sorted(
            candidates,
            key=lambda item: (
                item.distance_km is None,
                item.distance_km if item.distance_km is not None else 999999.0,
                item.id,
            ),
        )

    async def dispatch_next_offer(self, *, order_id: int) -> RiderDispatchOfferResponse | None:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        if order.status not in {OrderStatus.preparing, OrderStatus.placed}:
            return None
        if order.restaurant is None:
            return None

        restaurant = order.restaurant
        candidates = await self._dispatch_candidates_for_order(order, restaurant)
        if not candidates:
            order.rider_assignment_state = "open_unfilled"
            order.rider_assignment_tier = None
            order.rider_offer_expires_at = None
            await self.session.commit()
            return None

        chosen = candidates[0]
        offer = OrderDispatchOffer(
            order_id=order.id,
            restaurant_id=restaurant.id,
            rider_user_id=chosen.id,
            tier=chosen.assignment_type,
            status="pending",
            round_number=order.rider_assignment_round + 1,
            rank_index=0,
            expires_at=datetime.now(UTC) + timedelta(seconds=self._timeout_for_tier(restaurant, chosen.assignment_type)),
        )
        self.session.add(offer)
        order.rider_assignment_state = f"offered_{chosen.assignment_type}"
        order.rider_assignment_tier = chosen.assignment_type
        order.rider_assignment_round += 1
        order.rider_offer_expires_at = offer.expires_at
        await self.session.commit()
        await self.session.refresh(offer)
        await self._notify_rider_offer(order, offer)
        try:
            from app.tasks.rider_dispatch import expire_dispatch_offer

            expire_dispatch_offer.apply_async(args=[offer.id], countdown=self._timeout_for_tier(restaurant, chosen.assignment_type))
        except Exception:
            pass
        return self._build_offer_response(offer)

    async def accept_offer(self, *, user: User, offer_id: int) -> RiderDispatchOfferResponse:
        offer = await self.session.get(OrderDispatchOffer, offer_id)
        if offer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found.")
        if offer.rider_user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This offer is not assigned to you.")
        if offer.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer is no longer pending.")
        if offer.expires_at and offer.expires_at < datetime.now(UTC):
            offer.status = "expired"
            await self.session.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Offer already expired.")

        order = await self.order_repo.get_by_id(offer.order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
        order.rider_user_id = user.id
        order.rider_assigned_at = order.rider_assigned_at or datetime.now(UTC)
        if order.status == OrderStatus.placed:
            order.status = OrderStatus.preparing
            order.preparing_at = order.preparing_at or datetime.now(UTC)
        order.rider_assignment_state = "assigned"
        order.rider_assignment_tier = offer.tier
        order.rider_offer_expires_at = None
        offer.status = "accepted"
        offer.responded_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(offer)
        return self._build_offer_response(offer)

    async def reject_offer(self, *, user: User, offer_id: int) -> RiderDispatchOfferResponse:
        offer = await self.session.get(OrderDispatchOffer, offer_id)
        if offer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found.")
        if offer.rider_user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This offer is not assigned to you.")
        if offer.status != "pending":
            return self._build_offer_response(offer)
        offer.status = "rejected"
        offer.responded_at = datetime.now(UTC)
        order = await self.order_repo.get_by_id(offer.order_id)
        if order is not None and order.rider_user_id is None:
            order.rider_assignment_state = "unassigned"
            order.rider_assignment_tier = None
            order.rider_offer_expires_at = None
        await self.session.commit()
        await self.session.refresh(offer)
        await self.dispatch_next_offer(order_id=offer.order_id)
        return self._build_offer_response(offer)

    async def expire_offer(self, *, offer_id: int) -> None:
        offer = await self.session.get(OrderDispatchOffer, offer_id)
        if offer is None or offer.status != "pending":
            return
        if offer.expires_at and offer.expires_at > datetime.now(UTC):
            return
        offer.status = "expired"
        offer.responded_at = datetime.now(UTC)
        order = await self.order_repo.get_by_id(offer.order_id)
        if order is not None and order.rider_user_id is None:
            order.rider_assignment_state = "unassigned"
            order.rider_assignment_tier = None
            order.rider_offer_expires_at = None
        await self.session.commit()
        await self.dispatch_next_offer(order_id=offer.order_id)

    async def _notify_rider_offer(self, order: Order, offer: OrderDispatchOffer) -> None:
        payload = {
            "event": "rider_offer",
            "event_id": f"order-{order.id}-offer-{offer.id}",
            "audience": "rider",
            "category": "order_dispatch",
            "order_id": order.id,
            "order_number": order.order_number,
            "restaurant_id": order.restaurant_id,
            "restaurant_name": order.restaurant.name if order.restaurant else "Unknown",
            "rider_user_id": offer.rider_user_id,
            "tier": offer.tier,
            "offer_id": offer.id,
            "expires_at": offer.expires_at.isoformat() if offer.expires_at else None,
            "title": "New delivery request",
            "body": f"Order {order.order_number} is ready for rider assignment.",
            "deep_link": f"/rider/orders/{order.id}",
        }
        try:
            await self.notifications.create_notification_from_payload(
                recipient_user_id=offer.rider_user_id,
                payload=payload,
                actor_user_id=None,
            )
        except Exception:
            pass
        try:
            await realtime_bus.publish(ORDER_RIDER_CHANNEL, payload)
        except Exception:
            pass

    async def _dispatch_candidates_for_order(
        self,
        order: Order,
        restaurant: Restaurant,
    ) -> list[RiderDispatchCandidateResponse]:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.roles).selectinload(UserRole.role),
                selectinload(User.restaurant_assignments),
            )
            .where(User.is_active.is_(True))
        )
        users = result.scalars().unique().all()
        ranked: list[RiderDispatchCandidateResponse] = []
        for user in users:
            if not self._user_is_rider(user):
                continue
            if self._is_busy(user):
                continue
            candidate = self._build_candidate(user, restaurant, order)
            if candidate is not None:
                if restaurant.rider_dispatch_policy == "private_only" and candidate.assignment_type != "rider_private":
                    continue
                ranked.append(candidate)

        tier_order = {"rider_private": 0, "rider_preferred": 1, "open": 2}
        return sorted(
            ranked,
            key=lambda item: (
                tier_order.get(item.assignment_type, 99),
                item.distance_km is None,
                item.distance_km if item.distance_km is not None else 999999.0,
                item.id,
            ),
        )

    def _build_candidate(self, user: User, restaurant: Restaurant, order: Order | None) -> RiderDispatchCandidateResponse | None:
        assignment_type = self._candidate_assignment_type(user, restaurant.id)
        if assignment_type is None:
            return None
        if user.rider_work_mode == "assigned" and assignment_type == "open":
            return None
        distance_km = self._distance_to_restaurant(user, restaurant)
        return RiderDispatchCandidateResponse(
            id=user.id,
            full_name=user.full_name,
            phone=user.phone,
            avatar_url=user.avatar_url,
            assignment_type=assignment_type,
            rider_work_mode=user.rider_work_mode,
            busy=self._is_busy(user),
            distance_km=distance_km,
            current_latitude=user.current_latitude,
            current_longitude=user.current_longitude,
        )

    def _candidate_assignment_type(self, user: User, restaurant_id: int) -> str | None:
        assignment_types = {
            assignment.assignment_type
            for assignment in user.restaurant_assignments
            if assignment.restaurant_id == restaurant_id
        }
        if assignment_types.intersection({"rider_private", "private_rider"}):
            return "rider_private"
        if assignment_types.intersection({"rider_preferred", "preferred_rider"}):
            return "rider_preferred"
        if "rider" in {role.role.code for role in user.roles} and user.rider_work_mode == "freelance":
            return "open"
        if assignment_types.intersection({"rider", "rider_open", "open_rider"}):
            return "open"
        return None

    def _user_is_rider(self, user: User) -> bool:
        return any(role.role.code == "rider" for role in user.roles)

    def _is_busy(self, user: User) -> bool:
        # Treat any in-flight order as busy for open dispatch.
        return False

    def _distance_to_restaurant(self, user: User, restaurant: Restaurant) -> float | None:
        if None in {user.current_latitude, user.current_longitude, restaurant.latitude, restaurant.longitude}:
            return None
        return round(
            self._haversine_km(
                user.current_latitude or 0.0,
                user.current_longitude or 0.0,
                restaurant.latitude or 0.0,
                restaurant.longitude or 0.0,
            ),
            2,
        )

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _timeout_for_tier(self, restaurant: Restaurant, tier: str) -> int:
        if tier == "rider_private":
            return restaurant.rider_private_offer_timeout_seconds
        if tier == "rider_preferred":
            return restaurant.rider_preferred_offer_timeout_seconds
        return restaurant.rider_open_offer_timeout_seconds

    async def _require_managed_restaurant(self, user_id: int, restaurant_id: int) -> Restaurant:
        workspace_repo = WorkspaceRepository(self.session)
        workspace = await workspace_repo.get_active_workspace(user_id)
        if workspace is None or workspace.workspace_type != "merchant" or workspace.primary_restaurant_id != restaurant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to manage this restaurant.")
        restaurant = await self.session.get(Restaurant, restaurant_id)
        if restaurant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found.")
        return restaurant

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    def _build_invitation_response(self, invitation: RestaurantRiderInvitation) -> RiderInvitationResponse:
        return RiderInvitationResponse(
            id=invitation.id,
            restaurant_id=invitation.restaurant_id,
            inviter_user_id=invitation.inviter_user_id,
            invited_user_id=invitation.invited_user_id,
            invited_email=invitation.invited_email,
            invitation_type=invitation.invitation_type,
            status=invitation.status,
            notes=invitation.notes,
            responded_at=invitation.responded_at,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at,
        )

    def _build_offer_response(self, offer: OrderDispatchOffer) -> RiderDispatchOfferResponse:
        return RiderDispatchOfferResponse(
            id=offer.id,
            order_id=offer.order_id,
            restaurant_id=offer.restaurant_id,
            rider_user_id=offer.rider_user_id,
            tier=offer.tier,
            status=offer.status,
            round_number=offer.round_number,
            rank_index=offer.rank_index,
            expires_at=offer.expires_at,
            responded_at=offer.responded_at,
            created_at=offer.created_at,
            updated_at=offer.updated_at,
        )
