"""module customer_invoices v1

Revision ID: 61e7f8780fe2
Revises: 17f5e53eba64
Create Date: 2026-08-13T09:14:16.135129+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "61e7f8780fe2"
down_revision = '17f5e53eba64'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_customer_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('invoice_number', sa.String(length=255), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_customers.id'), nullable=False),
        sa.Column('so_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_sales_orders.id'), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False, server_default='draft'),
        sa.Column('total', sa.Numeric(18, 4), nullable=True),
    )
    op.create_index('ix_biz_customer_invoices_client_code', 'biz_customer_invoices', ['client_code'])
    op.add_column('biz_customer_invoice_lines', sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_customer_invoice_lines_invoice_id', 'biz_customer_invoice_lines', 'biz_customer_invoices', ['invoice_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_customer_invoice_lines_invoice_id', 'biz_customer_invoice_lines', ['invoice_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
