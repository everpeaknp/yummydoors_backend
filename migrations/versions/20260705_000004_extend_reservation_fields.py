"""Extend reservation fields for merchant operations and Flutter parity.

Revision ID: 20260705_000004
Revises: 20260705_000003
Create Date: 2026-07-05 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260705_000004"
down_revision = "20260705_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("table_reservations", sa.Column("occasion", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("table_reservations", "occasion")
