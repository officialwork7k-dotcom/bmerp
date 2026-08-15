"""Posting engine core: journal_entries + journal_lines (see
infrastructure/posting.py) and ModuleMetadata.posting_rules (pure JSONB on
the existing `modules.metadata` column — no schema change needed for that
half).

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), nullable=True),
        sa.Column("document_module", sa.String(length=64), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=255), server_default="", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="posted", nullable=False),
        sa.Column("reversal_of", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal_entries.id"), nullable=True),
        sa.Column("posted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_journal_entries_document", "journal_entries", ["document_module", "document_id"])

    op.create_table(
        "journal_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("account_code", sa.String(length=64), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=False),
        sa.Column("debit", sa.Numeric(18, 4), server_default="0", nullable=False),
        sa.Column("credit", sa.Numeric(18, 4), server_default="0", nullable=False),
    )
    op.create_index("ix_journal_lines_entry", "journal_lines", ["journal_entry_id"])


def downgrade() -> None:
    op.drop_table("journal_lines")
    op.drop_table("journal_entries")
