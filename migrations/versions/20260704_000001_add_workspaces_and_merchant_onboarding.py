"""add workspaces and merchant onboarding

Revision ID: 20260704_000001
Revises: 804d2c11c0a0
Create Date: 2026-07-04 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260704_000001"
down_revision = "804d2c11c0a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("is_personal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("primary_restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workspaces_workspace_type", "workspaces", ["workspace_type"], unique=False)
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)

    op.create_table(
        "workspace_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("membership_role", sa.String(length=50), nullable=False, server_default="member"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )

    op.add_column("users", sa.Column("active_workspace_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_active_workspace_id_workspaces",
        "users",
        "workspaces",
        ["active_workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "merchant_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("admin_notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_merchant_applications_status", "merchant_applications", ["status"], unique=False)

    op.create_table(
        "merchant_restaurant_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("merchant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False, server_default="create_external"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_name", sa.String(length=255), nullable=False),
        sa.Column("requested_slug", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("area", sa.String(length=100), nullable=True),
        sa.Column("source_system", sa.String(length=50), nullable=False, server_default="yummydoors"),
        sa.Column("pos_restaurant_id", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.execute(
        """
        INSERT INTO workspaces (workspace_type, name, slug, status, is_personal, metadata_json, created_at, updated_at)
        SELECT
            'customer',
            COALESCE(full_name, 'User') || ' Customer',
            NULL,
            'active',
            true,
            json_build_object('owner_user_id', id),
            NOW(),
            NOW()
        FROM users
        """
    )
    op.execute(
        """
        INSERT INTO workspace_memberships (workspace_id, user_id, membership_role, status, is_primary, created_at, updated_at)
        SELECT
            w.id,
            u.id,
            'owner',
            'active',
            true,
            NOW(),
            NOW()
        FROM users u
        JOIN workspaces w
          ON w.workspace_type = 'customer'
         AND (w.metadata_json ->> 'owner_user_id')::integer = u.id
        """
    )
    op.execute(
        """
        UPDATE users u
        SET active_workspace_id = w.id
        FROM workspaces w
        WHERE w.workspace_type = 'customer'
          AND (w.metadata_json ->> 'owner_user_id')::integer = u.id
        """
    )


def downgrade() -> None:
    op.drop_table("merchant_restaurant_requests")
    op.drop_index("ix_merchant_applications_status", table_name="merchant_applications")
    op.drop_table("merchant_applications")
    op.drop_constraint("fk_users_active_workspace_id_workspaces", "users", type_="foreignkey")
    op.drop_column("users", "active_workspace_id")
    op.drop_table("workspace_memberships")
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.drop_index("ix_workspaces_workspace_type", table_name="workspaces")
    op.drop_table("workspaces")
