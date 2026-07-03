"""restaurant discovery foundation

Revision ID: 20260702_000003
Revises: 20260702_000002
Create Date: 2026-07-02 00:00:03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260702_000003"
down_revision = "20260702_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("cover_image_url", sa.String(length=500), nullable=True))
    op.add_column("restaurants", sa.Column("logo_url", sa.String(length=500), nullable=True))
    op.add_column("restaurants", sa.Column("short_description", sa.String(length=500), nullable=True))
    op.add_column("restaurants", sa.Column("primary_cuisine_label", sa.String(length=100), nullable=True))
    op.add_column("restaurants", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("restaurants", sa.Column("area", sa.String(length=100), nullable=True))
    op.add_column("restaurants", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("restaurants", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column(
        "restaurants",
        sa.Column("rating_average", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "restaurants",
        sa.Column("review_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "restaurants",
        sa.Column("supports_delivery", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "restaurants",
        sa.Column("has_free_delivery", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("restaurants", sa.Column("offer_text", sa.String(length=255), nullable=True))
    op.add_column("restaurants", sa.Column("delivery_eta_min_minutes", sa.Integer(), nullable=True))
    op.add_column("restaurants", sa.Column("delivery_eta_max_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "restaurants",
        sa.Column("sort_rank", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "restaurants",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    op.create_table(
        "restaurant_categories",
        sa.Column(
            "restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    category_table = sa.table(
        "categories",
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_featured", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        category_table,
        [
            {"slug": "all", "name": "All", "sort_order": 0, "is_featured": True, "is_active": True},
            {"slug": "momo", "name": "Momo", "sort_order": 10, "is_featured": True, "is_active": True},
            {"slug": "coffee", "name": "Coffee", "sort_order": 20, "is_featured": True, "is_active": True},
            {"slug": "pizza", "name": "Pizza", "sort_order": 30, "is_featured": True, "is_active": True},
            {"slug": "burger", "name": "Burger", "sort_order": 40, "is_featured": True, "is_active": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("restaurant_categories")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")
    op.drop_column("restaurants", "is_featured")
    op.drop_column("restaurants", "sort_rank")
    op.drop_column("restaurants", "delivery_eta_max_minutes")
    op.drop_column("restaurants", "delivery_eta_min_minutes")
    op.drop_column("restaurants", "offer_text")
    op.drop_column("restaurants", "has_free_delivery")
    op.drop_column("restaurants", "supports_delivery")
    op.drop_column("restaurants", "review_count")
    op.drop_column("restaurants", "rating_average")
    op.drop_column("restaurants", "longitude")
    op.drop_column("restaurants", "latitude")
    op.drop_column("restaurants", "area")
    op.drop_column("restaurants", "city")
    op.drop_column("restaurants", "primary_cuisine_label")
    op.drop_column("restaurants", "short_description")
    op.drop_column("restaurants", "logo_url")
    op.drop_column("restaurants", "cover_image_url")
