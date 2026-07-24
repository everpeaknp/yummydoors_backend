"""Add cookie modal promo placement."""

from alembic import op


revision = "20260725_000001"
down_revision = "eda3351b75e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE promoplacement ADD VALUE IF NOT EXISTS 'cookie_modal'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    pass
