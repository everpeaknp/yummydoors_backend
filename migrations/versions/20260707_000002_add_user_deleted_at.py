"""Add soft-delete timestamp to users.

Revision ID: 20260707_000002
Revises: 20260707_000001
Create Date: 2026-07-07 18:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260707_000002"
down_revision = "20260707_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "deleted_at")
