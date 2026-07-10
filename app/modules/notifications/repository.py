from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import FcmDeviceToken, WebPushSubscription
from app.modules.restaurants.models import RestaurantUserAssignment
from app.modules.workspaces.models import Workspace, WorkspaceMembership


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_subscription_by_endpoint(self, endpoint: str) -> WebPushSubscription | None:
        result = await self.session.execute(
            select(WebPushSubscription).where(WebPushSubscription.endpoint == endpoint)
        )
        return result.scalar_one_or_none()

    async def upsert_web_push_subscription(
        self,
        *,
        user_id: int,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: str | None,
    ) -> WebPushSubscription:
        record = await self.get_subscription_by_endpoint(endpoint)
        if record is None:
            record = WebPushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_agent=user_agent,
                is_active=True,
            )
            self.session.add(record)
        else:
            record.user_id = user_id
            record.p256dh = p256dh
            record.auth = auth
            record.user_agent = user_agent
            record.is_active = True

        await self.session.flush()
        return record

    async def deactivate_subscription(self, endpoint: str) -> bool:
        record = await self.get_subscription_by_endpoint(endpoint)
        if record is None:
            return False
        record.is_active = False
        await self.session.flush()
        return True

    async def list_active_subscriptions_for_user(self, user_id: int) -> list[WebPushSubscription]:
        result = await self.session.execute(
            select(WebPushSubscription).where(
                WebPushSubscription.user_id == user_id,
                WebPushSubscription.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def count_active_subscriptions_for_user(self, user_id: int) -> int:
        return len(await self.list_active_subscriptions_for_user(user_id))

    async def get_fcm_token(self, token: str) -> FcmDeviceToken | None:
        result = await self.session.execute(
            select(FcmDeviceToken).where(FcmDeviceToken.token == token)
        )
        return result.scalar_one_or_none()

    async def upsert_fcm_token(
        self,
        *,
        user_id: int,
        token: str,
        platform: str | None,
        user_agent: str | None,
    ) -> FcmDeviceToken:
        record = await self.get_fcm_token(token)
        now = datetime.now(UTC)
        if record is None:
            record = FcmDeviceToken(
                user_id=user_id,
                token=token,
                platform=platform,
                user_agent=user_agent,
                is_active=True,
                last_seen_at=now,
            )
            self.session.add(record)
        else:
            record.user_id = user_id
            record.platform = platform
            record.user_agent = user_agent
            record.is_active = True
            record.last_seen_at = now

        await self.session.flush()
        return record

    async def deactivate_fcm_token(self, token: str) -> bool:
        record = await self.get_fcm_token(token)
        if record is None:
            return False
        record.is_active = False
        await self.session.flush()
        return True

    async def list_active_fcm_tokens_for_user(self, user_id: int) -> list[FcmDeviceToken]:
        result = await self.session.execute(
            select(FcmDeviceToken).where(
                FcmDeviceToken.user_id == user_id,
                FcmDeviceToken.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def count_active_fcm_tokens_for_user(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(FcmDeviceToken).where(
                FcmDeviceToken.user_id == user_id,
                FcmDeviceToken.is_active.is_(True),
            )
        )
        return int(result.scalar_one() or 0)

    async def list_merchant_user_ids_for_restaurant(self, restaurant_id: int) -> list[int]:
        workspace_result = await self.session.execute(
            select(WorkspaceMembership.user_id)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(
                Workspace.workspace_type == "merchant",
                Workspace.primary_restaurant_id == restaurant_id,
                WorkspaceMembership.status == "active",
            )
        )
        workspace_user_ids = set(workspace_result.scalars().all())

        assignment_result = await self.session.execute(
            select(RestaurantUserAssignment.user_id).where(
                RestaurantUserAssignment.restaurant_id == restaurant_id
            )
        )
        assignment_user_ids = set(assignment_result.scalars().all())

        return sorted(workspace_user_ids | assignment_user_ids)
