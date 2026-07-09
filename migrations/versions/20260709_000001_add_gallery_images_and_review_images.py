"""add gallery images and review images

Revision ID: 20260709_000001
Revises: 5f3c4070b994
Create Date: 2026-07-09

"""
from alembic import op
import sqlalchemy as sa

revision = "20260709_000001"
down_revision = "5f3c4070b994"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "restaurant_gallery_images",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("caption", sa.String(255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_restaurant_gallery_images_restaurant_id",
        "restaurant_gallery_images",
        ["restaurant_id"],
    )

    op.add_column(
        "restaurant_reviews",
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_restaurant_reviews_order_id", "restaurant_reviews", ["order_id"])

    try:
        op.drop_constraint(
            "uq_restaurant_reviews_user_restaurant", "restaurant_reviews", type_="unique"
        )
    except Exception:
        pass  # may not exist in all environments

    op.create_unique_constraint(
        "uq_restaurant_reviews_order", "restaurant_reviews", ["order_id"]
    )

    op.create_table(
        "restaurant_review_images",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "review_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_restaurant_review_images_review_id",
        "restaurant_review_images",
        ["review_id"],
    )


def downgrade() -> None:
    op.drop_table("restaurant_review_images")
    try:
        op.drop_constraint(
            "uq_restaurant_reviews_order", "restaurant_reviews", type_="unique"
        )
    except Exception:
        pass
    op.drop_index("ix_restaurant_reviews_order_id", "restaurant_reviews")
    op.drop_column("restaurant_reviews", "order_id")
    op.create_unique_constraint(
        "uq_restaurant_reviews_user_restaurant",
        "restaurant_reviews",
        ["user_id", "restaurant_id"],
    )
    op.drop_table("restaurant_gallery_images")
