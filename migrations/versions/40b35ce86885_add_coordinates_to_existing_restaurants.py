"""Add coordinates to existing restaurants

Revision ID: 40b35ce86885
Revises: 20260708_000001
Create Date: 2026-07-08 06:14:21.404718
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '40b35ce86885'
down_revision = '20260708_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update existing restaurants with coordinates so they appear on the map
    op.execute(
        """
        UPDATE restaurants 
        SET latitude = 28.2100, longitude = 83.9860 
        WHERE slug = 'mario-pizza';
        """
    )
    op.execute(
        """
        UPDATE restaurants 
        SET latitude = 28.2080, longitude = 83.9850 
        WHERE slug = 'burger-hub';
        """
    )

def downgrade() -> None:
    pass
