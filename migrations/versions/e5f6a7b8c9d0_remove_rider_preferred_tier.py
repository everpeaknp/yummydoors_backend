"""Remove the rider_preferred dispatch tier.

Simplifies the rider model to three tiers: private (restaurant's own
team), open (freelance pool), and platform (platform-onboarded fallback).
"Preferred" never had a distinct payout/behavior from private beyond a
different offer timeout — folding it into private is a strict
simplification, not a loss of capability: existing preferred riders keep
their restaurant access, just under the private tier going forward.

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-08-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Anyone currently on the preferred tier keeps their restaurant access —
    # just reclassified as private rather than dropped.
    op.execute(
        sa.text(
            "UPDATE restaurant_user_assignments "
            "SET assignment_type = 'rider_private' "
            "WHERE assignment_type IN ('rider_preferred', 'preferred_rider')"
        )
    )
    op.drop_column("restaurants", "rider_preferred_offer_timeout_seconds")


def downgrade() -> None:
    op.add_column(
        "restaurants",
        sa.Column("rider_preferred_offer_timeout_seconds", sa.Integer(), nullable=False, server_default="180"),
    )
    op.alter_column("restaurants", "rider_preferred_offer_timeout_seconds", server_default=None)
