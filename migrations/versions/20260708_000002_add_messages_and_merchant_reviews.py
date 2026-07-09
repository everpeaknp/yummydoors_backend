"""add messages and merchant reviews tables

Revision ID: 20260708_000002
Revises: 40b35ce86885
Create Date: 2026-07-08

"""
from alembic import op
import sqlalchemy as sa

revision = "20260708_000002"
down_revision = "40b35ce86885"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── messages ─────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sender_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_from_merchant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_messages_sender_user_id", "messages", ["sender_user_id"])
    op.create_index("ix_messages_restaurant_id", "messages", ["restaurant_id"])
    op.create_index("ix_messages_customer_user_id", "messages", ["customer_user_id"])

    # ── merchant_reviews ──────────────────────────────────────────────────────
    op.create_table(
        "merchant_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rating",
            sa.Integer(),
            sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_merchant_review_rating"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("merchant_reply", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_merchant_reviews_user_id", "merchant_reviews", ["user_id"])
    op.create_index("ix_merchant_reviews_restaurant_id", "merchant_reviews", ["restaurant_id"])


def downgrade() -> None:
    op.drop_table("merchant_reviews")
    op.drop_table("messages")
