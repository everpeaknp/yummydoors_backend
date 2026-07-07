"""Add review ownership and favorites.

Revision ID: 20260706_000001
Revises: 20260705_000004
Create Date: 2026-07-06 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260706_000001"
down_revision = "20260705_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("restaurant_reviews", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_restaurant_reviews_user_id"), "restaurant_reviews", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_restaurant_reviews_user_id_users",
        "restaurant_reviews",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_restaurant_reviews_user_restaurant",
        "restaurant_reviews",
        ["user_id", "restaurant_id"],
    )

    op.create_table(
        "user_favorite_restaurants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "restaurant_id", name="uq_user_favorite_restaurant"),
    )
    op.create_index(op.f("ix_user_favorite_restaurants_user_id"), "user_favorite_restaurants", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_user_favorite_restaurants_restaurant_id"),
        "user_favorite_restaurants",
        ["restaurant_id"],
        unique=False,
    )

    op.create_table(
        "user_favorite_menu_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "menu_item_id", name="uq_user_favorite_menu_item"),
    )
    op.create_index(op.f("ix_user_favorite_menu_items_user_id"), "user_favorite_menu_items", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_user_favorite_menu_items_menu_item_id"),
        "user_favorite_menu_items",
        ["menu_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_favorite_menu_items_menu_item_id"), table_name="user_favorite_menu_items")
    op.drop_index(op.f("ix_user_favorite_menu_items_user_id"), table_name="user_favorite_menu_items")
    op.drop_table("user_favorite_menu_items")

    op.drop_index(op.f("ix_user_favorite_restaurants_restaurant_id"), table_name="user_favorite_restaurants")
    op.drop_index(op.f("ix_user_favorite_restaurants_user_id"), table_name="user_favorite_restaurants")
    op.drop_table("user_favorite_restaurants")

    op.drop_constraint("uq_restaurant_reviews_user_restaurant", "restaurant_reviews", type_="unique")
    op.drop_constraint("fk_restaurant_reviews_user_id_users", "restaurant_reviews", type_="foreignkey")
    op.drop_index(op.f("ix_restaurant_reviews_user_id"), table_name="restaurant_reviews")
    op.drop_column("restaurant_reviews", "user_id")
