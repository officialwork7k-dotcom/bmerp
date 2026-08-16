"""org_invites (Phase 4) + ai_settings_overrides (Phase 5) — see OrgInvite/
AiSettingsOverride docstrings in infrastructure/models.py.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-16T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_org_invites_client_code", "org_invites", ["client_code"])
    op.execute(
        "CREATE UNIQUE INDEX uq_org_invites_pending_email ON org_invites (client_code, lower(email)) "
        "WHERE status = 'pending'"
    )

    op.create_table(
        "ai_settings_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider", sa.String(length=16), nullable=True),
        sa.Column("gemini_api_key", sa.String(length=512), nullable=True),
        sa.Column("gemini_model", sa.String(length=64), nullable=True),
        sa.Column("openai_api_key", sa.String(length=512), nullable=True),
        sa.Column("openai_model", sa.String(length=64), nullable=True),
        sa.Column("discount_tax_treatment", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_settings_overrides")
    op.execute("DROP INDEX IF EXISTS uq_org_invites_pending_email")
    op.drop_index("ix_org_invites_client_code", table_name="org_invites")
    op.drop_table("org_invites")
