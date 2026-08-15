"""Telegram integration for the AI assistant — bot config on the existing
ai_settings singleton (telegram_enabled/telegram_bot_token/
telegram_bot_username/public_base_url/telegram_update_offset), plus
telegram_link_codes (short-lived self-service link codes) and
telegram_links (the actual chat_id<->user mapping, one per user in v1).
See models.py's docstrings for the full design rationale.

Revision ID: a3f6c8d1e207
Revises: d94a1f6c2b83
Create Date: 2026-08-16T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a3f6c8d1e207"
down_revision = "d94a1f6c2b83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_settings", sa.Column("telegram_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("ai_settings", sa.Column("telegram_bot_token", sa.String(length=128), nullable=True))
    op.add_column("ai_settings", sa.Column("telegram_bot_username", sa.String(length=64), nullable=True))
    op.add_column("ai_settings", sa.Column("public_base_url", sa.String(length=256), nullable=True))
    op.add_column("ai_settings", sa.Column("telegram_update_offset", sa.BigInteger(), nullable=True))

    op.create_table(
        "telegram_link_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_telegram_link_codes_code"),
    )
    op.create_index("ix_telegram_link_codes_user", "telegram_link_codes", ["user_id"])

    op.create_table(
        "telegram_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("preferred_client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="SET NULL"), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_telegram_links_user"),
        sa.UniqueConstraint("telegram_chat_id", name="uq_telegram_links_chat_id"),
    )


def downgrade() -> None:
    op.drop_table("telegram_links")
    op.drop_index("ix_telegram_link_codes_user", table_name="telegram_link_codes")
    op.drop_table("telegram_link_codes")
    op.drop_column("ai_settings", "telegram_update_offset")
    op.drop_column("ai_settings", "public_base_url")
    op.drop_column("ai_settings", "telegram_bot_username")
    op.drop_column("ai_settings", "telegram_bot_token")
    op.drop_column("ai_settings", "telegram_enabled")
