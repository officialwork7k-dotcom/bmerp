"""module customer_receipts v1

Revision ID: 32618f2a5fa8
Revises: 61e7f8780fe2
Create Date: 2026-08-13T09:14:34.325464+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "32618f2a5fa8"
down_revision = '61e7f8780fe2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_customer_receipts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_customers.id'), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_customer_invoices.id'), nullable=False),
        sa.Column('amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('receipt_date', sa.Date(), nullable=False),
        sa.Column('method', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=False, server_default='draft'),
    )
    op.create_index('ix_biz_customer_receipts_client_code', 'biz_customer_receipts', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
