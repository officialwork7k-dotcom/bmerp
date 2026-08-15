"""module customer_invoices v13

Revision ID: 886c7febd75d
Revises: e79cf2b2eac6
Create Date: 2026-08-14T15:54:10.994953+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "886c7febd75d"
down_revision = 'e79cf2b2eac6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customer_invoices', sa.Column('currency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_currencies.id'), nullable=True))
    op.add_column('biz_customer_invoices', sa.Column('payment_terms', sa.String(length=255), nullable=True))
    op.add_column('biz_customer_invoices', sa.Column('customer_po_reference', sa.String(length=255), nullable=True))
    op.add_column('biz_customer_invoices', sa.Column('posting_date', sa.Date(), nullable=True))
    op.add_column('biz_customer_invoices', sa.Column('salesperson', sa.String(length=255), nullable=True))
    op.add_column('biz_customer_invoices', sa.Column('dunning_block', sa.Boolean(), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
