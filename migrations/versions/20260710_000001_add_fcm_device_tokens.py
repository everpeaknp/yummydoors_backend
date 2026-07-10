"""add fcm device tokens

Revision ID: 20260710_000001
Revises: 20260709_000002
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = "20260710_000001"
down_revision = "20260709_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fcm_device_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=1024), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=True),
        sa.Column("user_agent", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "token", name="uq_fcm_device_token_user_token"),
    )
    op.create_index("ix_fcm_device_tokens_user_id", "fcm_device_tokens", ["user_id"])
    op.create_index("ix_fcm_device_tokens_token", "fcm_device_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_fcm_device_tokens_token", table_name="fcm_device_tokens")
    op.drop_index("ix_fcm_device_tokens_user_id", table_name="fcm_device_tokens")
    op.drop_table("fcm_device_tokens")
