"""Home feed parity — add favorite_count to menu_items and create featured_videos table.

Revision ID: 20260708_000001
Revises: 20260707_000002
Create Date: 2026-07-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_000001"
down_revision = "20260707_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "menu_items",
        sa.Column("favorite_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "featured_videos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subtitle", sa.String(500), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_featured_videos_sort_order", "featured_videos", ["sort_order"])


def downgrade() -> None:
    op.drop_index("ix_featured_videos_sort_order", table_name="featured_videos")
    op.drop_table("featured_videos")
    op.drop_column("menu_items", "favorite_count")
