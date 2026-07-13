"""add rider offer availability

Revision ID: 20260712_000002
Revises: 20260712_000001
Create Date: 2026-07-12 12:00:02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260712_000002"
down_revision = "20260712_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_accepting_offers",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_accepting_offers")
