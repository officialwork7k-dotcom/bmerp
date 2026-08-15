"""module vendor_invoices v20

Revision ID: 50c7b8e8aa1e
Revises: 89ab0aea3549
Create Date: 2026-08-14T15:53:38.670150+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "50c7b8e8aa1e"
down_revision = '89ab0aea3549'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendor_invoices', sa.Column('currency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_currencies.id'), nullable=True))
    op.add_column('biz_vendor_invoices', sa.Column('payment_terms', sa.String(length=255), nullable=True))
    op.add_column('biz_vendor_invoices', sa.Column('vendor_reference', sa.String(length=255), nullable=True))
    op.add_column('biz_vendor_invoices', sa.Column('posting_date', sa.Date(), nullable=True))
    op.add_column('biz_vendor_invoices', sa.Column('payment_block', sa.Boolean(), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
