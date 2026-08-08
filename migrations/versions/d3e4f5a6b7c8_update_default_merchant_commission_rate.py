"""Update default Restaurant.commission_rate_percent from 15% to 18%.

The 15% default shipped minutes earlier in c1d2e3f4a5b6 was an unresearched
placeholder. Pathao Food's published rider-commission split research also
surfaced their merchant commission rate (~18%) as the closer, more directly
comparable real-market benchmark (vs. Foodmandu's ~22%) — updating the
default to match rather than leaving an invented number in place.

Only backfills restaurants still sitting at the old 15.0 default (i.e.
nobody has customized their rate yet) — any restaurant already given an
explicit override is left untouched.

Revision ID: d3e4f5a6b7c8
Revises: c1d2e3f4a5b6
Create Date: 2026-08-08 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d3e4f5a6b7c8"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("restaurants", "commission_rate_percent", server_default="18.0")
    op.execute(
        sa.text("UPDATE restaurants SET commission_rate_percent = 18.0 WHERE commission_rate_percent = 15.0")
    )
    op.alter_column("restaurants", "commission_rate_percent", server_default=None)


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE restaurants SET commission_rate_percent = 15.0 WHERE commission_rate_percent = 18.0")
    )
