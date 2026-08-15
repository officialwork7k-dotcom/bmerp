"""Persist the attached scan on an AI conversation message (image_data +
image_mime_type, bytea in Postgres) so it survives a conversation reload
instead of only showing live in the current browser session — this was
the only reason a photo sent via Telegram (or the web uploader) vanished
from chat history on revisit. Not stored via infrastructure/storage.py's
S3 adapter: unconfigured (no endpoint/credentials) in this environment.

Revision ID: c7a91e4f3b56
Revises: a3f6c8d1e207
Create Date: 2026-08-16T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "c7a91e4f3b56"
down_revision = "a3f6c8d1e207"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_conversation_messages", sa.Column("image_data", sa.LargeBinary(), nullable=True))
    op.add_column("ai_conversation_messages", sa.Column("image_mime_type", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_conversation_messages", "image_mime_type")
    op.drop_column("ai_conversation_messages", "image_data")
