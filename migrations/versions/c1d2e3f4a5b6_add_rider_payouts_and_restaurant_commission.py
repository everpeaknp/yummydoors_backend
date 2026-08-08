"""Add rider_payouts table and Restaurant.commission_rate_percent.

Revision ID: c1d2e3f4a5b6
Revises: b7c8d9e0f1a2
Create Date: 2026-08-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurants",
        sa.Column("commission_rate_percent", sa.Float(), nullable=False, server_default="15.0"),
    )
    op.alter_column("restaurants", "commission_rate_percent", server_default=None)

    op.create_table(
        "rider_payouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("rider_user_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("base_fare", sa.Float(), nullable=False),
        sa.Column("distance_fare", sa.Float(), nullable=False),
        sa.Column("gross_fare", sa.Float(), nullable=False),
        sa.Column("commission_rate_percent", sa.Float(), nullable=False),
        sa.Column("commission_amount", sa.Float(), nullable=False),
        sa.Column("payout_amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rider_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_rider_payouts_order_id"),
    )
    op.create_index("ix_rider_payouts_rider_user_id", "rider_payouts", ["rider_user_id"])
    op.create_index("ix_rider_payouts_restaurant_id", "rider_payouts", ["restaurant_id"])
    op.alter_column("rider_payouts", "status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_rider_payouts_restaurant_id", table_name="rider_payouts")
    op.drop_index("ix_rider_payouts_rider_user_id", table_name="rider_payouts")
    op.drop_table("rider_payouts")
    op.drop_column("restaurants", "commission_rate_percent")
