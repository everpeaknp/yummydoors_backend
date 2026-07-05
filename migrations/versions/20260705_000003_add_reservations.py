"""Add restaurant tables and customer reservations.

Revision ID: 20260705_000003
Revises: 20260705_000002
Create Date: 2026-07-05 10:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260705_000003"
down_revision = "20260705_000002"
branch_labels = None
depends_on = None


reservation_status_enum = postgresql.ENUM(
    "pending",
    "confirmed",
    "seated",
    "completed",
    "cancelled",
    "no_show",
    name="reservationstatus",
    create_type=False,
)


def upgrade() -> None:
    reservation_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "restaurant_tables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("zone", sa.String(length=100), nullable=True),
        sa.Column("min_guest_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_guest_count", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "code", name="uq_restaurant_table_code"),
    )
    op.create_index(op.f("ix_restaurant_tables_restaurant_id"), "restaurant_tables", ["restaurant_id"], unique=False)

    op.create_table(
        "table_reservations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=True),
        sa.Column("reservation_code", sa.String(length=32), nullable=False),
        sa.Column("status", reservation_status_enum, nullable=False),
        sa.Column("reservation_date", sa.Date(), nullable=False),
        sa.Column("reservation_time", sa.String(length=10), nullable=False),
        sa.Column("guest_count", sa.Integer(), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("special_request", sa.String(length=1000), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="yummydoors"),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["restaurant_tables.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_table_reservations_customer_id"), "table_reservations", ["customer_id"], unique=False)
    op.create_index(op.f("ix_table_reservations_restaurant_id"), "table_reservations", ["restaurant_id"], unique=False)
    op.create_index(op.f("ix_table_reservations_table_id"), "table_reservations", ["table_id"], unique=False)
    op.create_index(op.f("ix_table_reservations_reservation_code"), "table_reservations", ["reservation_code"], unique=True)
    op.create_index(op.f("ix_table_reservations_reservation_date"), "table_reservations", ["reservation_date"], unique=False)

    op.create_table(
        "reservation_status_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("status", reservation_status_enum, nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reservation_id"], ["table_reservations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reservation_status_events_reservation_id"),
        "reservation_status_events",
        ["reservation_id"],
        unique=False,
    )

    op.alter_column("restaurant_tables", "min_guest_count", server_default=None)
    op.alter_column("restaurant_tables", "max_guest_count", server_default=None)
    op.alter_column("restaurant_tables", "status", server_default=None)
    op.alter_column("restaurant_tables", "sort_order", server_default=None)
    op.alter_column("table_reservations", "source", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_reservation_status_events_reservation_id"), table_name="reservation_status_events")
    op.drop_table("reservation_status_events")

    op.drop_index(op.f("ix_table_reservations_reservation_date"), table_name="table_reservations")
    op.drop_index(op.f("ix_table_reservations_reservation_code"), table_name="table_reservations")
    op.drop_index(op.f("ix_table_reservations_table_id"), table_name="table_reservations")
    op.drop_index(op.f("ix_table_reservations_restaurant_id"), table_name="table_reservations")
    op.drop_index(op.f("ix_table_reservations_customer_id"), table_name="table_reservations")
    op.drop_table("table_reservations")

    op.drop_index(op.f("ix_restaurant_tables_restaurant_id"), table_name="restaurant_tables")
    op.drop_table("restaurant_tables")

    reservation_status_enum.drop(op.get_bind(), checkfirst=True)
