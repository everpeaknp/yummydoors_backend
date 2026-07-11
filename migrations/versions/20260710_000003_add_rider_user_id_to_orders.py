"""add rider user id to orders

Revision ID: 20260710_000003
Revises: 20260710_000002
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260710_000003"
down_revision = "20260710_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("rider_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orders_rider_user_id_users",
        "orders",
        "users",
        ["rider_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_rider_user_id", "orders", ["rider_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_rider_user_id", table_name="orders")
    op.drop_constraint("fk_orders_rider_user_id_users", "orders", type_="foreignkey")
    op.drop_column("orders", "rider_user_id")
