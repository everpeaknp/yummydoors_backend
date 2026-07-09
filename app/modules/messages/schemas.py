from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    id: int
    content: str
    is_from_merchant: bool
    sender_name: str
    created_at: datetime
    read_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str


class ConversationSummary(BaseModel):
    customer_id: int
    customer_name: str
    customer_avatar: str | None = None
    last_message: str
    last_message_at: datetime
    unread_count: int

    model_config = ConfigDict(from_attributes=True)
