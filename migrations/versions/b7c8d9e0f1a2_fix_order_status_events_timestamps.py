"""Fix order_status_events missing server defaults on created_at/updated_at.

The table was created with created_at/updated_at as NOT NULL but no
server_default, unlike every other TimestampMixin-backed table. Since the
ORM never sets these columns explicitly (it relies on the server default
declared in the model), every insert into order_status_events — i.e. every
order status change, including customer/merchant order cancellation — has
been failing with a NotNullViolationError since the table was introduced.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-08-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "order_status_events",
        "created_at",
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "order_status_events",
        "updated_at",
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column("order_status_events", "created_at", server_default=None)
    op.alter_column("order_status_events", "updated_at", server_default=None)
