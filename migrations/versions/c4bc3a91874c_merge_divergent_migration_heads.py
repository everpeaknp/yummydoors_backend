"""merge divergent migration heads

Revision ID: c4bc3a91874c
Revises: 20260711_000001, 20260711_000002, 20260724_000001, 20260725_000001
Create Date: 2026-08-05 20:50:59.789410
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4bc3a91874c'
down_revision = ('20260711_000001', '20260711_000002', '20260724_000001', '20260725_000001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
