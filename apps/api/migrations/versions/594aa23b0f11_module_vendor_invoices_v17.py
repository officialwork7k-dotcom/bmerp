"""module vendor_invoices v17

Revision ID: 594aa23b0f11
Revises: 4a41e9c1712d
Create Date: 2026-08-13T18:12:32.261162+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "594aa23b0f11"
down_revision = '4a41e9c1712d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendor_invoices', sa.Column('total_charges', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_vendor_invoice_charges', sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_vendor_invoice_charges_invoice_id', 'biz_vendor_invoice_charges', 'biz_vendor_invoices', ['invoice_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_vendor_invoice_charges_invoice_id', 'biz_vendor_invoice_charges', ['invoice_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
