"""Add payments table and order payment_status column.

Revision ID: c8f1a2b3d4e5
Revises: c4bc3a91874c
Create Date: 2026-08-05 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c8f1a2b3d4e5"
down_revision = "c4bc3a91874c"
branch_labels = None
depends_on = None


payment_status_enum = postgresql.ENUM(
    "pending",
    "verified",
    "failed",
    "refunded",
    name="paymentstatus",
    create_type=False,
)


def upgrade() -> None:
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("provider_ref", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default="NPR"),
        sa.Column("status", payment_status_enum, nullable=False, server_default="pending"),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    op.create_index("ix_payments_provider_ref", "payments", ["provider_ref"])

    op.add_column(
        "orders",
        sa.Column("payment_status", sa.String(length=20), nullable=False, server_default="unpaid"),
    )


def downgrade() -> None:
    op.drop_column("orders", "payment_status")
    op.drop_index("ix_payments_provider_ref", table_name="payments")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    payment_status_enum.drop(op.get_bind(), checkfirst=True)
