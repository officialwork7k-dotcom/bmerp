"""Document flow / copy-with-reference engine: document_flow_links (see
infrastructure/document_flow.py) and ModuleMetadata.document_flows (pure
JSONB on the existing modules.metadata column).

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_flow_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), nullable=True),
        sa.Column("source_module", sa.String(length=64), nullable=False),
        sa.Column("source_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_module", sa.String(length=64), nullable=False),
        sa.Column("target_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_flow_links_source_line", "document_flow_links", ["source_module", "source_line_id"])


def downgrade() -> None:
    op.drop_table("document_flow_links")
