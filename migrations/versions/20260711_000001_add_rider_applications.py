"""add rider applications

Revision ID: 20260711_000001
Revises: 20260710_000002
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_000001"
down_revision = "20260710_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rider_applications",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("city_area", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("vehicle_type", sa.String(length=100), nullable=False),
        sa.Column("availability", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("admin_notes", sa.String(length=2000), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_rider_applications_user_id", "rider_applications", ["user_id"])
    op.create_index("ix_rider_applications_status", "rider_applications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_rider_applications_status", table_name="rider_applications")
    op.drop_index("ix_rider_applications_user_id", table_name="rider_applications")
    op.drop_table("rider_applications")
