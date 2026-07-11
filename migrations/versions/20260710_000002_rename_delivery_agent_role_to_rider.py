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
    bind = op.get_bind()
    rider_exists = bind.execute(sa.text("SELECT 1 FROM roles WHERE code = 'rider' LIMIT 1")).scalar()
    if rider_exists:
        bind.execute(
            sa.text(
                "UPDATE roles SET name = 'Rider', description = 'Delivery rider' WHERE code = 'rider'"
            )
        )
        bind.execute(sa.text("DELETE FROM roles WHERE code = 'delivery_agent'"))
        return

    bind.execute(
        sa.text(
            """
            UPDATE roles
            SET code = 'rider',
                name = 'Rider',
                description = 'Delivery rider'
            WHERE code = 'delivery_agent'
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    delivery_agent_exists = bind.execute(
        sa.text("SELECT 1 FROM roles WHERE code = 'delivery_agent' LIMIT 1")
    ).scalar()
    if delivery_agent_exists:
        bind.execute(
            sa.text(
                "UPDATE roles SET name = 'Delivery Agent', description = 'Delivery rider or agent' WHERE code = 'delivery_agent'"
            )
        )
        bind.execute(sa.text("DELETE FROM roles WHERE code = 'rider'"))
        return

    bind.execute(
        sa.text(
            """
            UPDATE roles
            SET code = 'delivery_agent',
                name = 'Delivery Agent',
                description = 'Delivery rider or agent'
            WHERE code = 'rider'
            """
        )
    )
