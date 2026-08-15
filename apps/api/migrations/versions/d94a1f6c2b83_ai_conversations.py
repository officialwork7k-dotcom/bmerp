"""AI chat: persist conversations (`ai_conversations` + `ai_conversation_messages`),
superseding the v1 "stateless, nothing persisted" scope decision now that
users need to browse/delete past chats and reference one from another by
number. Numbering is scoped to (user_id, client_code) — see AiConversation's
docstring for why.

Revision ID: d94a1f6c2b83
Revises: c2f8a4d0e716
Create Date: 2026-08-16T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d94a1f6c2b83"
down_revision = "c2f8a4d0e716"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), nullable=False),
        sa.Column("seq_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "client_code", "seq_number", name="uq_ai_conversations_user_client_seq"),
    )
    op.create_index("ix_ai_conversations_user_client", "ai_conversations", ["user_id", "client_code"])

    op.create_table(
        "ai_conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_conversation_messages_conversation", "ai_conversation_messages", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_conversation_messages_conversation", table_name="ai_conversation_messages")
    op.drop_table("ai_conversation_messages")
    op.drop_index("ix_ai_conversations_user_client", table_name="ai_conversations")
    op.drop_table("ai_conversations")
