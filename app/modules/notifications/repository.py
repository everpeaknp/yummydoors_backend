from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import FcmDeviceToken, UserNotification, WebPushSubscription
from app.modules.restaurants.models import RestaurantUserAssignment
from app.modules.workspaces.models import Workspace, WorkspaceMembership


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_notification_by_event_key(
        self,
        *,
        recipient_user_id: int,
        event_key: str,
    ) -> UserNotification | None:
        result = await self.session.execute(
            select(UserNotification).where(
                UserNotification.recipient_user_id == recipient_user_id,
                UserNotification.event_key == event_key,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_user_notification(
        self,
        *,
        recipient_user_id: int,
        audience: str,
        category: str,
        event_key: str,
        title: str,
        body: str,
        deep_link: str | None,
        payload_json: dict | None,
        restaurant_id: int | None = None,
        order_id: int | None = None,
        message_id: int | None = None,
        actor_user_id: int | None = None,
    ) -> UserNotification:
        record = await self.get_user_notification_by_event_key(
            recipient_user_id=recipient_user_id,
            event_key=event_key,
        )
        if record is None:
            record = UserNotification(
                recipient_user_id=recipient_user_id,
                audience=audience,
                category=category,
                event_key=event_key,
                title=title,
                body=body,
                deep_link=deep_link,
                payload_json=payload_json,
                restaurant_id=restaurant_id,
                order_id=order_id,
                message_id=message_id,
                actor_user_id=actor_user_id,
            )
            self.session.add(record)
            await self.session.flush()
            return record

        record.audience = audience
        record.category = category
        record.title = title
        record.body = body
        record.deep_link = deep_link
        record.payload_json = payload_json
        record.restaurant_id = restaurant_id
        record.order_id = order_id
        record.message_id = message_id
        record.actor_user_id = actor_user_id
        await self.session.flush()
        return record

    async def list_user_notifications(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
        unread_only: bool = False,
        include_dismissed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UserNotification]:
        stmt = select(UserNotification).where(UserNotification.recipient_user_id == recipient_user_id)
        if audience is not None:
            stmt = stmt.where(UserNotification.audience == audience)
        if restaurant_id is not None:
            stmt = stmt.where(UserNotification.restaurant_id == restaurant_id)
        if unread_only:
            stmt = stmt.where(UserNotification.read_at.is_(None))
        if not include_dismissed:
            stmt = stmt.where(UserNotification.dismissed_at.is_(None))

        stmt = stmt.order_by(UserNotification.created_at.desc(), UserNotification.id.desc())
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_user_notifications(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
        unread_only: bool = False,
        include_dismissed: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(UserNotification).where(
            UserNotification.recipient_user_id == recipient_user_id
        )
        if audience is not None:
            stmt = stmt.where(UserNotification.audience == audience)
        if restaurant_id is not None:
            stmt = stmt.where(UserNotification.restaurant_id == restaurant_id)
        if unread_only:
            stmt = stmt.where(UserNotification.read_at.is_(None))
        if not include_dismissed:
            stmt = stmt.where(UserNotification.dismissed_at.is_(None))

        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def mark_user_notification_read(
        self,
        *,
        recipient_user_id: int,
        notification_id: int,
    ) -> UserNotification | None:
        record = await self.session.get(UserNotification, notification_id)
        if record is None or record.recipient_user_id != recipient_user_id:
            return None
        if record.read_at is None:
            record.read_at = datetime.now(UTC)
        await self.session.flush()
        return record

    async def mark_all_user_notifications_read(
        self,
        *,
        recipient_user_id: int,
        audience: str | None = None,
        restaurant_id: int | None = None,
    ) -> int:
        values = {"read_at": datetime.now(UTC)}
        stmt = update(UserNotification).where(
            UserNotification.recipient_user_id == recipient_user_id,
            UserNotification.read_at.is_(None),
            UserNotification.dismissed_at.is_(None),
        )
        if audience is not None:
            stmt = stmt.where(UserNotification.audience == audience)
        if restaurant_id is not None:
            stmt = stmt.where(UserNotification.restaurant_id == restaurant_id)
        result = await self.session.execute(stmt.values(**values))
        await self.session.flush()
        return int(result.rowcount or 0)

    async def dismiss_user_notification(
        self,
        *,
        recipient_user_id: int,
        notification_id: int,
    ) -> UserNotification | None:
        record = await self.session.get(UserNotification, notification_id)
        if record is None or record.recipient_user_id != recipient_user_id:
            return None
        if record.dismissed_at is None:
            record.dismissed_at = datetime.now(UTC)
        await self.session.flush()
        return record

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
                RestaurantUserAssignment.restaurant_id == restaurant_id,
                RestaurantUserAssignment.assignment_type != "rider",
            )
        )
        assignment_user_ids = set(assignment_result.scalars().all())

        return sorted(workspace_user_ids | assignment_user_ids)
