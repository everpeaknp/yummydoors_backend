"""Add rider_reviews.

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-08-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rider_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("rider_user_id", sa.Integer(), nullable=False),
        sa.Column("customer_user_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rider_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_rider_reviews_order"),
    )
    op.alter_column("rider_reviews", "is_published", server_default=None)
    op.create_index("ix_rider_reviews_rider_user_id", "rider_reviews", ["rider_user_id"])
    op.create_index("ix_rider_reviews_customer_user_id", "rider_reviews", ["customer_user_id"])


def downgrade() -> None:
    op.drop_index("ix_rider_reviews_customer_user_id", table_name="rider_reviews")
    op.drop_index("ix_rider_reviews_rider_user_id", table_name="rider_reviews")
    op.drop_table("rider_reviews")
