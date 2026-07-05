"""add active restaurant context

Revision ID: 20260704_000002
Revises: 20260704_000001
Create Date: 2026-07-04 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260704_000002"
down_revision = "20260704_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("active_restaurant_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_active_restaurant_id_restaurants",
        "users",
        "restaurants",
        ["active_restaurant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_active_restaurant_id_restaurants", "users", type_="foreignkey")
    op.drop_column("users", "active_restaurant_id")
