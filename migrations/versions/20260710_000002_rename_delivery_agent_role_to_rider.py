"""rename delivery agent role to rider

Revision ID: 20260710_000002
Revises: 20260710_000001
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260710_000002"
down_revision = "20260710_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE roles
            SET code = 'rider',
                name = 'Rider',
                description = 'Delivery rider'
            WHERE code IN ('delivery_agent', 'rider')
            """
        )
    )
    op.execute(sa.text("DELETE FROM roles WHERE code = 'delivery_agent'"))


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE roles
            SET code = 'delivery_agent',
                name = 'Delivery Agent',
                description = 'Delivery rider or agent'
            WHERE code IN ('rider', 'delivery_agent')
            """
        )
    )
    op.execute(sa.text("DELETE FROM roles WHERE code = 'rider'"))
