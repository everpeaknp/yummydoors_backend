from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewResponse(BaseModel):
    id: int
    user_id: int
    reviewer_name: str
    rating: int
    content: str | None = None
    merchant_reply: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    content: str | None = Field(default=None, max_length=2000)


class ReplyRequest(BaseModel):
    reply: str = Field(min_length=1, max_length=2000)
