"""module vendor_invoice_lines v16

Revision ID: 34c62bd87551
Revises: e9f2762a6aed
Create Date: 2026-08-13T11:42:29.372221+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "34c62bd87551"
down_revision = 'e9f2762a6aed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('biz_vendor_invoice_lines', 'description', nullable=True)


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
