"""add rider dispatch workflow

Revision ID: 20260712_000001
Revises: 20260711_000005
Create Date: 2026-07-12 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260712_000001"
down_revision = "20260711_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("rider_work_mode", sa.String(length=32), nullable=False, server_default="freelance"),
    )
    op.add_column(
        "restaurants",
        sa.Column("rider_dispatch_policy", sa.String(length=32), nullable=False, server_default="ranked"),
    )
    op.add_column(
        "restaurants",
        sa.Column(
            "rider_private_offer_timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
    )
    op.add_column(
        "restaurants",
        sa.Column(
            "rider_preferred_offer_timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default="180",
        ),
    )
    op.add_column(
        "restaurants",
        sa.Column(
            "rider_open_offer_timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default="300",
        ),
    )
    op.add_column(
        "orders",
        sa.Column("rider_assignment_state", sa.String(length=32), nullable=False, server_default="unassigned"),
    )
    op.add_column(
        "orders",
        sa.Column("rider_assignment_tier", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("rider_assignment_round", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "orders",
        sa.Column("rider_offer_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "restaurant_rider_invitations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("inviter_user_id", sa.Integer(), nullable=False),
        sa.Column("invited_user_id", sa.Integer(), nullable=True),
        sa.Column("invited_email", sa.String(length=255), nullable=False),
        sa.Column("invitation_type", sa.String(length=32), nullable=False, server_default="private"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_restaurant_rider_invitations_restaurant_id",
        "restaurant_rider_invitations",
        ["restaurant_id"],
    )
    op.create_index(
        "ix_restaurant_rider_invitations_inviter_user_id",
        "restaurant_rider_invitations",
        ["inviter_user_id"],
    )
    op.create_index(
        "ix_restaurant_rider_invitations_invited_user_id",
        "restaurant_rider_invitations",
        ["invited_user_id"],
    )
    op.create_index(
        "ix_restaurant_rider_invitations_invited_email",
        "restaurant_rider_invitations",
        ["invited_email"],
    )

    op.create_table(
        "order_dispatch_offers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("rider_user_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rank_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rider_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("order_id", "rider_user_id", "round_number", name="uq_order_dispatch_offer_round"),
    )
    op.create_index("ix_order_dispatch_offers_order_id", "order_dispatch_offers", ["order_id"])
    op.create_index("ix_order_dispatch_offers_restaurant_id", "order_dispatch_offers", ["restaurant_id"])
    op.create_index("ix_order_dispatch_offers_rider_user_id", "order_dispatch_offers", ["rider_user_id"])
    op.create_index("ix_order_dispatch_offers_expires_at", "order_dispatch_offers", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_order_dispatch_offers_expires_at", table_name="order_dispatch_offers")
    op.drop_index("ix_order_dispatch_offers_rider_user_id", table_name="order_dispatch_offers")
    op.drop_index("ix_order_dispatch_offers_restaurant_id", table_name="order_dispatch_offers")
    op.drop_index("ix_order_dispatch_offers_order_id", table_name="order_dispatch_offers")
    op.drop_table("order_dispatch_offers")

    op.drop_index("ix_restaurant_rider_invitations_invited_email", table_name="restaurant_rider_invitations")
    op.drop_index("ix_restaurant_rider_invitations_invited_user_id", table_name="restaurant_rider_invitations")
    op.drop_index("ix_restaurant_rider_invitations_inviter_user_id", table_name="restaurant_rider_invitations")
    op.drop_index("ix_restaurant_rider_invitations_restaurant_id", table_name="restaurant_rider_invitations")
    op.drop_table("restaurant_rider_invitations")

    op.drop_column("orders", "rider_offer_expires_at")
    op.drop_column("orders", "rider_assignment_round")
    op.drop_column("orders", "rider_assignment_tier")
    op.drop_column("orders", "rider_assignment_state")

    op.drop_column("restaurants", "rider_open_offer_timeout_seconds")
    op.drop_column("restaurants", "rider_preferred_offer_timeout_seconds")
    op.drop_column("restaurants", "rider_private_offer_timeout_seconds")
    op.drop_column("restaurants", "rider_dispatch_policy")

    op.drop_column("users", "rider_work_mode")
