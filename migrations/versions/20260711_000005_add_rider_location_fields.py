"""add rider location fields

Revision ID: 20260711_000005
Revises: 20260711_000004
Create Date: 2026-07-11 00:00:05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260711_000005"
down_revision = "20260711_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("current_latitude", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("current_longitude", sa.Float(), nullable=True))
    op.add_column(
        "users",
        sa.Column("current_location_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "current_location_updated_at")
    op.drop_column("users", "current_longitude")
    op.drop_column("users", "current_latitude")
