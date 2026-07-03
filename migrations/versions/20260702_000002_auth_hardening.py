"""auth hardening

Revision ID: 20260702_000002
Revises: 20260702_000001
Create Date: 2026-07-02 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260702_000002"
down_revision = "20260702_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_rate_limits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("action", "key", name="uq_auth_rate_limit_action_key"),
    )
    op.create_index("ix_auth_rate_limits_action", "auth_rate_limits", ["action"], unique=False)
    op.create_index("ix_auth_rate_limits_key", "auth_rate_limits", ["key"], unique=False)

    op.create_table(
        "auth_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_auth_audit_logs_action", "auth_audit_logs", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_audit_logs_action", table_name="auth_audit_logs")
    op.drop_table("auth_audit_logs")
    op.drop_index("ix_auth_rate_limits_key", table_name="auth_rate_limits")
    op.drop_index("ix_auth_rate_limits_action", table_name="auth_rate_limits")
    op.drop_table("auth_rate_limits")
