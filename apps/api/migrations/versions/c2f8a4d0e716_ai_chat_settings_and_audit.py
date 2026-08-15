"""AI chat assistant: `ai_settings` (singleton, admin-only, keys never
exposed via generic module CRUD — see AiSettings docstring) and
`ai_tool_calls` (audit trail for every tool the assistant invoked).

Revision ID: c2f8a4d0e716
Revises: b7e5a2f0c94d
Create Date: 2026-08-14T00:10:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c2f8a4d0e716"
down_revision = "594166d558ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("provider", sa.String(length=16), server_default="gemini", nullable=False),
        sa.Column("gemini_api_key", sa.String(length=512), nullable=True),
        sa.Column("gemini_model", sa.String(length=64), server_default="gemini-2.0-flash", nullable=False),
        sa.Column("openai_api_key", sa.String(length=512), nullable=True),
        sa.Column("openai_model", sa.String(length=64), server_default="gpt-4o-mini", nullable=False),
        sa.Column("auto_post_amount_cap", sa.Numeric(18, 4), nullable=True),
        sa.Column("write_allowed_modules", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "ai_tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("tool", sa.String(length=64), nullable=False),
        sa.Column("args", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("result_summary", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_tool_calls_conversation", "ai_tool_calls", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_tool_calls_conversation", table_name="ai_tool_calls")
    op.drop_table("ai_tool_calls")
    op.drop_table("ai_settings")
