"""Open items + manual clearing: `clearings` + `clearing_items` (see
infrastructure/clearing.py) and ModuleMetadata.clearing_config (pure JSONB
on the existing modules.metadata column).

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clearings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), nullable=True),
        sa.Column("description", sa.String(length=255), server_default="", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("cleared_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cleared_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "clearing_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("clearing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clearings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
    )
    op.create_index("ix_clearing_items_module_record", "clearing_items", ["module", "record_id"])


def downgrade() -> None:
    op.drop_table("clearing_items")
    op.drop_table("clearings")
