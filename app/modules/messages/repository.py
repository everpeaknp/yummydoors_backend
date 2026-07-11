from __future__ import annotations

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.messages.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_conversations(self, restaurant_id: int) -> list[dict]:
        """Return one summary row per unique customer for a restaurant."""
        # Subquery: latest message timestamp per customer
        sq = (
            select(
                Message.customer_user_id,
                func.max(Message.created_at).label("last_message_at"),
            )
            .where(Message.restaurant_id == restaurant_id)
            .group_by(Message.customer_user_id)
            .subquery()
        )

        stmt = (
            select(Message)
            .options(selectinload(Message.customer), selectinload(Message.sender))
            .join(
                sq,
                and_(
                    Message.customer_user_id == sq.c.customer_user_id,
                    Message.created_at == sq.c.last_message_at,
                ),
            )
            .where(Message.restaurant_id == restaurant_id)
            .order_by(sq.c.last_message_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_unread_count(self, restaurant_id: int, customer_user_id: int) -> int:
        stmt = select(func.count()).where(
            Message.restaurant_id == restaurant_id,
            Message.customer_user_id == customer_user_id,
            Message.is_from_merchant.is_(False),
            Message.read_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_conversation(
        self, restaurant_id: int, customer_user_id: int
    ) -> list[Message]:
        stmt = (
            select(Message)
            .options(selectinload(Message.sender))
            .where(
                Message.restaurant_id == restaurant_id,
                Message.customer_user_id == customer_user_id,
            )
            .order_by(Message.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_message(
        self,
        *,
        sender_user_id: int,
        restaurant_id: int,
        customer_user_id: int,
        content: str,
        is_from_merchant: bool,
    ) -> Message:
        msg = Message(
            sender_user_id=sender_user_id,
            restaurant_id=restaurant_id,
            customer_user_id=customer_user_id,
            content=content,
            is_from_merchant=is_from_merchant,
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        # Reload relationships
        stmt = (
            select(Message)
            .options(
                selectinload(Message.sender),
                selectinload(Message.customer),
                selectinload(Message.restaurant),
            )
            .where(Message.id == msg.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def mark_conversation_read(
        self, restaurant_id: int, customer_user_id: int
    ) -> None:
        from datetime import UTC, datetime

        await self.session.execute(
            update(Message)
            .where(
                Message.restaurant_id == restaurant_id,
                Message.customer_user_id == customer_user_id,
                Message.is_from_merchant.is_(False),
                Message.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        await self.session.commit()

    async def total_unread_for_restaurant(self, restaurant_id: int) -> int:
        stmt = select(func.count()).where(
            Message.restaurant_id == restaurant_id,
            Message.is_from_merchant.is_(False),
            Message.read_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # --- Customer-specific methods ---
    async def list_customer_conversations(self, customer_user_id: int) -> list[dict]:
        """Return one summary row per unique restaurant for a customer."""
        sq = (
            select(
                Message.restaurant_id,
                func.max(Message.created_at).label("last_message_at"),
            )
            .where(Message.customer_user_id == customer_user_id)
            .group_by(Message.restaurant_id)
            .subquery()
        )

        stmt = (
            select(Message)
            .options(selectinload(Message.restaurant), selectinload(Message.sender))
            .join(
                sq,
                and_(
                    Message.restaurant_id == sq.c.restaurant_id,
                    Message.created_at == sq.c.last_message_at,
                ),
            )
            .where(Message.customer_user_id == customer_user_id)
            .order_by(sq.c.last_message_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_unread_count_for_customer(self, customer_user_id: int, restaurant_id: int) -> int:
        stmt = select(func.count()).where(
            Message.restaurant_id == restaurant_id,
            Message.customer_user_id == customer_user_id,
            Message.is_from_merchant.is_(True),
            Message.read_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def mark_customer_conversation_read(
        self, customer_user_id: int, restaurant_id: int
    ) -> None:
        from datetime import UTC, datetime

        await self.session.execute(
            update(Message)
            .where(
                Message.restaurant_id == restaurant_id,
                Message.customer_user_id == customer_user_id,
                Message.is_from_merchant.is_(True),
                Message.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        await self.session.commit()
