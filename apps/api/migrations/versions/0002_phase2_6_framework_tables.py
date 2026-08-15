"""Phase 2-6 framework tables: roles, api_tokens, webhooks, number_series,
saved_views, notifications, approval_requests + users role/lockout columns.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "40878fb18dfe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True),
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("module_permissions", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.add_column("users", sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=True))
    op.add_column("users", sa.Column("failed_login_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "api_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("events", postgresql.JSONB(), server_default='["create","update","delete"]', nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhooks_module", "webhooks", ["module"])

    op.create_table(
        "number_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("prefix", sa.String(length=32), server_default="''", nullable=False),
        sa.Column("pad_width", sa.Integer(), server_default="5", nullable=False),
        sa.Column("reset_policy", sa.String(length=16), server_default="'never'", nullable=False),
        sa.Column("period_key", sa.String(length=16), server_default="''", nullable=False),
        sa.Column("next_value", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_unique_constraint("uq_number_series_module_field_period", "number_series", ["module", "field", "period_key"])

    op.create_table(
        "saved_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_saved_views_module_user", "saved_views", ["module", "user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=2000), server_default="''", nullable=False),
        sa.Column("link", sa.String(length=512), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])

    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=64), nullable=False),
        sa.Column("to_status", sa.String(length=64), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="'pending'", nullable=False),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approval_requests_module_record", "approval_requests", ["module", "record_id"])

    # Bootstrap: one Administrator role with is_admin=true, and either
    # promote an existing seed user or create a default admin account —
    # otherwise turning on enforcement would immediately lock everyone out
    # with no way back in.
    op.execute(
        "INSERT INTO roles (name, is_admin, module_permissions) VALUES ('Administrator', true, '{}') "
        "ON CONFLICT (name) DO NOTHING"
    )
    op.execute(
        """
        UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'Administrator')
        WHERE role_id IS NULL
        """
    )
    op.execute(
        """
        INSERT INTO users (username, password_hash, display_name, role_id)
        SELECT 'admin', '$argon2id$v=19$m=65536,t=3,p=4$AuAcY4wxhrC2FqKU0jonBA$dUovaVDLf+9nsYnNNvLlMoGnzmJcxo27R6dQlVCmVS4',
               'Administrator', (SELECT id FROM roles WHERE name = 'Administrator')
        WHERE NOT EXISTS (SELECT 1 FROM users)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_approval_requests_module_record", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index("ix_notifications_user_read", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_saved_views_module_user", table_name="saved_views")
    op.drop_table("saved_views")
    op.drop_constraint("uq_number_series_module_field_period", "number_series", type_="unique")
    op.drop_table("number_series")
    op.drop_index("ix_webhooks_module", table_name="webhooks")
    op.drop_table("webhooks")
    op.drop_table("api_tokens")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "role_id")
    op.drop_table("roles")
