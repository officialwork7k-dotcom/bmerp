"""module vendor_invoices v8

Revision ID: 3385fd1945ad
Revises: ca09eb37ff0e
Create Date: 2026-08-13T11:09:46.203130+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3385fd1945ad"
down_revision = 'ca09eb37ff0e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendor_invoices', sa.Column('invoice_number', sa.String(length=255), nullable=True))
    op.add_column('biz_vendor_invoices', sa.Column('gr_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_goods_receipts.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
