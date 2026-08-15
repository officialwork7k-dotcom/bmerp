"""module vendor_invoices v1

Revision ID: 619bad4bb452
Revises: ce1ac289a2b0
Create Date: 2026-08-12T06:09:22.227537+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "619bad4bb452"
down_revision = 'ce1ac289a2b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_vendor_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendors.id'), nullable=False),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_purchase_orders.id'), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('total', sa.Numeric(18, 4), nullable=True),
    )
    op.add_column('biz_vendor_invoice_lines', sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_vendor_invoice_lines_invoice_id', 'biz_vendor_invoice_lines', 'biz_vendor_invoices', ['invoice_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_vendor_invoice_lines_invoice_id', 'biz_vendor_invoice_lines', ['invoice_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
