"""Add push_delivery_failures outbox table.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-08-05 22:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_delivery_failures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("target", sa.String(length=1000), nullable=False),
        sa.Column("event_key", sa.String(length=128), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "channel", "target", "event_key", name="uq_push_delivery_failure_target"
        ),
    )
    op.create_index("ix_push_delivery_failures_user_id", "push_delivery_failures", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_push_delivery_failures_user_id", table_name="push_delivery_failures")
    op.drop_table("push_delivery_failures")
