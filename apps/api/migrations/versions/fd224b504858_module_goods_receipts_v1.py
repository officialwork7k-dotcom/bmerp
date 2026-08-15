"""module goods_receipts v1

Revision ID: fd224b504858
Revises: 1eba157f62de
Create Date: 2026-08-13T09:00:03.704994+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "fd224b504858"
down_revision = '1eba157f62de'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_goods_receipts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('gr_number', sa.String(length=255), nullable=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendors.id'), nullable=False),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_purchase_orders.id'), nullable=True),
        sa.Column('gr_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False, server_default='draft'),
        sa.Column('total_value', sa.Numeric(18, 4), nullable=True),
    )
    op.create_index('ix_biz_goods_receipts_client_code', 'biz_goods_receipts', ['client_code'])
    op.add_column('biz_goods_receipt_lines', sa.Column('gr_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_goods_receipt_lines_gr_id', 'biz_goods_receipt_lines', 'biz_goods_receipts', ['gr_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_goods_receipt_lines_gr_id', 'biz_goods_receipt_lines', ['gr_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
