"""Add richer restaurant discovery fields and reviews

Revision ID: 20260705_000001
Revises: 20260704_000002_add_active_restaurant_context
Create Date: 2026-07-05 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260705_000001"
down_revision = "acf0ecbbc747"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("supports_pickup", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("restaurants", sa.Column("supports_table_booking", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("restaurants", sa.Column("contact_phone", sa.String(length=32), nullable=True))
    op.add_column("restaurants", sa.Column("contact_email", sa.String(length=255), nullable=True))
    op.add_column("restaurants", sa.Column("opening_time", sa.String(length=10), nullable=True))
    op.add_column("restaurants", sa.Column("closing_time", sa.String(length=10), nullable=True))
    op.add_column("restaurants", sa.Column("about_text", sa.String(length=4000), nullable=True))
    op.add_column("restaurants", sa.Column("facilities_text", sa.String(length=4000), nullable=True))

    op.create_table(
        "restaurant_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("comment", sa.String(length=4000), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="yummydoors"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_restaurant_reviews_restaurant_id"), "restaurant_reviews", ["restaurant_id"], unique=False)

    op.alter_column("restaurants", "supports_pickup", server_default=None)
    op.alter_column("restaurants", "supports_table_booking", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_restaurant_reviews_restaurant_id"), table_name="restaurant_reviews")
    op.drop_table("restaurant_reviews")

    op.drop_column("restaurants", "facilities_text")
    op.drop_column("restaurants", "about_text")
    op.drop_column("restaurants", "closing_time")
    op.drop_column("restaurants", "opening_time")
    op.drop_column("restaurants", "contact_email")
    op.drop_column("restaurants", "contact_phone")
    op.drop_column("restaurants", "supports_table_booking")
    op.drop_column("restaurants", "supports_pickup")
