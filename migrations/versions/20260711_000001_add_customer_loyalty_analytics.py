"""add customer loyalty analytics columns

Revision ID: 20260711_000001
Revises: 20260710_000003
Create Date: 2026-07-11 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260711_000001"
down_revision = "20260710_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("total_spent", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("loyalty_points", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("loyalty_points_earned", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("loyalty_points_redeemed", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("users", "loyalty_points_redeemed")
    op.drop_column("users", "loyalty_points_earned")
    op.drop_column("users", "loyalty_points")
    op.drop_column("users", "total_spent")
    op.drop_column("users", "total_orders")
