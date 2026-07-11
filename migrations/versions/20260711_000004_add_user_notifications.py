"""add persisted user notifications

Revision ID: 20260711_000004
Revises: 20260710_000003
Create Date: 2026-07-11 00:00:04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260711_000004"
down_revision = "20260710_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("audience", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("deep_link", sa.String(length=1000), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("recipient_user_id", "event_key", name="uq_user_notifications_recipient_event"),
    )
    op.create_index("ix_user_notifications_recipient_user_id", "user_notifications", ["recipient_user_id"])
    op.create_index("ix_user_notifications_audience", "user_notifications", ["audience"])
    op.create_index("ix_user_notifications_category", "user_notifications", ["category"])
    op.create_index("ix_user_notifications_event_key", "user_notifications", ["event_key"])
    op.create_index("ix_user_notifications_restaurant_id", "user_notifications", ["restaurant_id"])
    op.create_index("ix_user_notifications_order_id", "user_notifications", ["order_id"])
    op.create_index("ix_user_notifications_message_id", "user_notifications", ["message_id"])
    op.create_index("ix_user_notifications_actor_user_id", "user_notifications", ["actor_user_id"])
    op.create_index("ix_user_notifications_read_at", "user_notifications", ["read_at"])


def downgrade() -> None:
    op.drop_index("ix_user_notifications_read_at", table_name="user_notifications")
    op.drop_index("ix_user_notifications_actor_user_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_message_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_order_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_restaurant_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_event_key", table_name="user_notifications")
    op.drop_index("ix_user_notifications_category", table_name="user_notifications")
    op.drop_index("ix_user_notifications_audience", table_name="user_notifications")
    op.drop_index("ix_user_notifications_recipient_user_id", table_name="user_notifications")
    op.drop_table("user_notifications")
