"""Expand carts and orders for checkout parity.

Revision ID: 20260705_000002
Revises: 20260705_000001
Create Date: 2026-07-05 00:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260705_000002"
down_revision = "20260705_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("carts", sa.Column("address_id", sa.Integer(), nullable=True))
    op.add_column("carts", sa.Column("coupon_code", sa.String(length=64), nullable=True))
    op.add_column("carts", sa.Column("coupon_discount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("carts", sa.Column("delivery_fee", sa.Float(), nullable=False, server_default="0"))
    op.add_column("carts", sa.Column("service_fee", sa.Float(), nullable=False, server_default="0"))
    op.add_column("carts", sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("carts", sa.Column("subtotal_amount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("carts", sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("carts", sa.Column("needs_cutlery", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("carts", sa.Column("cooking_request", sa.String(length=1000), nullable=True))
    op.add_column("carts", sa.Column("delivery_instruction", sa.String(length=1000), nullable=True))
    op.create_foreign_key(
        "fk_carts_address_id_customer_addresses",
        "carts",
        "customer_addresses",
        ["address_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("orders", sa.Column("payment_method", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("address_id", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("delivery_address_text", sa.String(length=1000), nullable=True))
    op.add_column("orders", sa.Column("delivery_recipient_name", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("delivery_phone_number", sa.String(length=32), nullable=True))
    op.add_column("orders", sa.Column("delivery_latitude", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("delivery_longitude", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("coupon_code", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("coupon_discount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("delivery_fee", sa.Float(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("service_fee", sa.Float(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("subtotal_amount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("needs_cutlery", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("orders", sa.Column("cooking_request", sa.String(length=1000), nullable=True))
    op.add_column("orders", sa.Column("delivery_instruction", sa.String(length=1000), nullable=True))
    op.add_column("orders", sa.Column("estimated_delivery_window", sa.String(length=100), nullable=True))
    op.add_column("orders", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("preparing_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("rider_assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_orders_address_id_customer_addresses",
        "orders",
        "customer_addresses",
        ["address_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column("carts", "coupon_discount", server_default=None)
    op.alter_column("carts", "delivery_fee", server_default=None)
    op.alter_column("carts", "service_fee", server_default=None)
    op.alter_column("carts", "tax_amount", server_default=None)
    op.alter_column("carts", "subtotal_amount", server_default=None)
    op.alter_column("carts", "total_amount", server_default=None)
    op.alter_column("carts", "needs_cutlery", server_default=None)

    op.alter_column("orders", "coupon_discount", server_default=None)
    op.alter_column("orders", "delivery_fee", server_default=None)
    op.alter_column("orders", "service_fee", server_default=None)
    op.alter_column("orders", "tax_amount", server_default=None)
    op.alter_column("orders", "subtotal_amount", server_default=None)
    op.alter_column("orders", "needs_cutlery", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_orders_address_id_customer_addresses", "orders", type_="foreignkey")
    op.drop_column("orders", "cancelled_at")
    op.drop_column("orders", "delivered_at")
    op.drop_column("orders", "picked_up_at")
    op.drop_column("orders", "rider_assigned_at")
    op.drop_column("orders", "preparing_at")
    op.drop_column("orders", "confirmed_at")
    op.drop_column("orders", "estimated_delivery_window")
    op.drop_column("orders", "delivery_instruction")
    op.drop_column("orders", "cooking_request")
    op.drop_column("orders", "needs_cutlery")
    op.drop_column("orders", "subtotal_amount")
    op.drop_column("orders", "tax_amount")
    op.drop_column("orders", "service_fee")
    op.drop_column("orders", "delivery_fee")
    op.drop_column("orders", "coupon_discount")
    op.drop_column("orders", "coupon_code")
    op.drop_column("orders", "delivery_longitude")
    op.drop_column("orders", "delivery_latitude")
    op.drop_column("orders", "delivery_phone_number")
    op.drop_column("orders", "delivery_recipient_name")
    op.drop_column("orders", "delivery_address_text")
    op.drop_column("orders", "address_id")
    op.drop_column("orders", "payment_method")

    op.drop_constraint("fk_carts_address_id_customer_addresses", "carts", type_="foreignkey")
    op.drop_column("carts", "delivery_instruction")
    op.drop_column("carts", "cooking_request")
    op.drop_column("carts", "needs_cutlery")
    op.drop_column("carts", "total_amount")
    op.drop_column("carts", "subtotal_amount")
    op.drop_column("carts", "tax_amount")
    op.drop_column("carts", "service_fee")
    op.drop_column("carts", "delivery_fee")
    op.drop_column("carts", "coupon_discount")
    op.drop_column("carts", "coupon_code")
    op.drop_column("carts", "address_id")
