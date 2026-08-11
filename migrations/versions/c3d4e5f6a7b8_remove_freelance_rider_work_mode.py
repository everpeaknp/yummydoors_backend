"""Drop the self-service "freelance" rider_work_mode value.

Only "assigned" (default, restaurant team / no open-pool dispatch) and
"platform" (admin-granted gig tier) remain. Existing riders in "freelance"
mode drop back to "assigned" -- consistent with how the admin-revoke path
already handles falling out of "platform".

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET rider_work_mode = 'assigned' WHERE rider_work_mode = 'freelance'")
    op.alter_column("users", "rider_work_mode", server_default="assigned")


def downgrade() -> None:
    op.alter_column("users", "rider_work_mode", server_default="freelance")
