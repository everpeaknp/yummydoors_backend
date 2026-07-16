"""add menu add-ons and cart/order selection snapshots

Revision ID: 20260716_000001
Revises: 20260712_000002
"""

from alembic import op
import sqlalchemy as sa


revision = "20260716_000001"
down_revision = "20260712_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "menu_add_ons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency_code", sa.String(length=10), nullable=False, server_default="NPR"),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_menu_add_ons_menu_item_id", "menu_add_ons", ["menu_item_id"])
    op.add_column("cart_items", sa.Column("modifier_ids", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("cart_items", sa.Column("add_on_selections", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("order_items", sa.Column("modifier_snapshot", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("order_items", sa.Column("add_on_snapshot", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("order_items", "add_on_snapshot")
    op.drop_column("order_items", "modifier_snapshot")
    op.drop_column("cart_items", "add_on_selections")
    op.drop_column("cart_items", "modifier_ids")
    op.drop_index("ix_menu_add_ons_menu_item_id", table_name="menu_add_ons")
    op.drop_table("menu_add_ons")
