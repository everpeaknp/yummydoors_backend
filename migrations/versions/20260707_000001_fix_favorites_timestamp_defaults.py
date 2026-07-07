"""Fix favorite timestamp defaults.

Revision ID: 20260707_000001
Revises: 20260706_000001
Create Date: 2026-07-07 17:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260707_000001"
down_revision = "20260706_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("user_favorite_restaurants", "user_favorite_menu_items"):
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )
        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )


def downgrade() -> None:
    for table_name in ("user_favorite_restaurants", "user_favorite_menu_items"):
        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
            existing_nullable=False,
        )
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
            existing_nullable=False,
        )
