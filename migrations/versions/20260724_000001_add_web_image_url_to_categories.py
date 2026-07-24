"""add desktop category image

Revision ID: 20260724_000001
Revises: 20260716_000001
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_000001"
down_revision = "20260716_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("web_image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "web_image_url")
