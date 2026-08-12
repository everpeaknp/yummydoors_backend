"""Replace gig-rider commission/wallet system with a salaried payroll model.

Platform-tier riders are now YummyDoors' own salaried staff (company bikes
provided), not commission-based gig workers -- there's no more per-delivery
fare/commission math and nothing for a wallet to debit. Drops the old
rider_payouts (per-order fare/commission ledger) and rider_wallets /
rider_wallet_transactions tables, replacing them with rider_salaries
(current monthly amount per rider, admin-set) and rider_payroll_payments
(one row per rider per pay period).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("rider_wallet_transactions")
    op.drop_table("rider_wallets")
    op.drop_table("rider_payouts")

    op.create_table(
        "rider_salaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rider_user_id", sa.Integer(), nullable=False),
        sa.Column("monthly_amount", sa.Float(), nullable=False),
        sa.Column("set_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rider_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rider_user_id", name="uq_rider_salaries_rider_user_id"),
    )

    op.create_table(
        "rider_payroll_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rider_user_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rider_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rider_user_id", "period", name="uq_rider_payroll_rider_period"),
    )
    op.alter_column("rider_payroll_payments", "status", server_default=None)
    op.create_index("ix_rider_payroll_payments_rider_user_id", "rider_payroll_payments", ["rider_user_id"])


def downgrade() -> None:
    op.drop_index("ix_rider_payroll_payments_rider_user_id", table_name="rider_payroll_payments")
    op.drop_table("rider_payroll_payments")
    op.drop_table("rider_salaries")

    op.create_table(
        "rider_payouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("rider_user_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("base_fare", sa.Float(), nullable=False),
        sa.Column("distance_fare", sa.Float(), nullable=False),
        sa.Column("gross_fare", sa.Float(), nullable=False),
        sa.Column("commission_rate_percent", sa.Float(), nullable=False),
        sa.Column("commission_amount", sa.Float(), nullable=False),
        sa.Column("payout_amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rider_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_rider_payouts_order_id"),
    )

    op.create_table(
        "rider_wallets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rider_user_id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rider_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rider_user_id", name="uq_rider_wallets_rider_user_id"),
    )

    op.create_table(
        "rider_wallet_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("balance_after", sa.Float(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["wallet_id"], ["rider_wallets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rider_wallet_transactions_wallet_id", "rider_wallet_transactions", ["wallet_id"])
