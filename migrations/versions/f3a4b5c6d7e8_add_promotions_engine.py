"""Add promotions/promotion_redemptions tables and seed the previously
hardcoded WELCOME50/SAVE10/FREEDEL coupon codes as real rows so existing
coupon behavior is preserved once the code stops special-casing them.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-08-05 22:40:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None

# NOTE: generic sa.Enum silently ignores create_type (it's a
# postgresql-dialect-specific flag only postgresql.ENUM honors). Using
# sa.Enum(create_type=False) here previously still let create_table()
# re-issue CREATE TYPE and crash with DuplicateObject. postgresql.ENUM
# with create_type=False is what actually suppresses that.
promotion_discount_type = postgresql.ENUM(
    "percentage", "fixed", "free_delivery", name="promotiondiscounttype", create_type=False
)


def upgrade() -> None:
    promotion_discount_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("discount_type", promotion_discount_type, nullable=False),
        sa.Column("discount_value", sa.Float(), nullable=False),
        sa.Column("max_discount_amount", sa.Float(), nullable=True),
        sa.Column("min_order_amount", sa.Float(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("per_user_limit", sa.Integer(), nullable=True),
        sa.Column("times_used", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_promotions_code", "promotions", ["code"])

    op.create_table(
        "promotion_redemptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("promotion_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["promotion_id"], ["promotions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    promotions_table = sa.table(
        "promotions",
        sa.column("code", sa.String),
        sa.column("discount_type", promotion_discount_type),
        sa.column("discount_value", sa.Float),
        sa.column("max_discount_amount", sa.Float),
        sa.column("min_order_amount", sa.Float),
        sa.column("is_active", sa.Boolean),
        sa.column("usage_limit", sa.Integer),
        sa.column("per_user_limit", sa.Integer),
        sa.column("times_used", sa.Integer),
        sa.column("description", sa.String),
    )
    # created_at/updated_at are left unset and fall back to the columns'
    # server_default=func.now() defined above.
    op.bulk_insert(
        promotions_table,
        [
            {
                "code": "WELCOME50",
                "discount_type": "fixed",
                "discount_value": 50.0,
                "max_discount_amount": None,
                "min_order_amount": 0.0,
                "is_active": True,
                "usage_limit": None,
                "per_user_limit": 1,
                "times_used": 0,
                "description": "Rs. 50 off for new customers.",
            },
            {
                "code": "SAVE10",
                "discount_type": "percentage",
                "discount_value": 10.0,
                "max_discount_amount": None,
                "min_order_amount": 0.0,
                "is_active": True,
                "usage_limit": None,
                "per_user_limit": None,
                "times_used": 0,
                "description": "10% off your order.",
            },
            {
                "code": "FREEDEL",
                "discount_type": "free_delivery",
                "discount_value": 0.0,
                "max_discount_amount": None,
                "min_order_amount": 0.0,
                "is_active": True,
                "usage_limit": None,
                "per_user_limit": None,
                "times_used": 0,
                "description": "Free delivery on your order.",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("promotion_redemptions")
    op.drop_index("ix_promotions_code", table_name="promotions")
    op.drop_table("promotions")
    promotion_discount_type.drop(op.get_bind(), checkfirst=True)
