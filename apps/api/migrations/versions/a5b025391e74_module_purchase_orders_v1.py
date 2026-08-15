"""module purchase_orders v1

Revision ID: a5b025391e74
Revises: b7d1deb2a0f1
Create Date: 2026-08-12T06:09:16.483367+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a5b025391e74"
down_revision = 'b7d1deb2a0f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_purchase_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendors.id'), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('subtotal', sa.Numeric(18, 4), nullable=True),
    )
    op.add_column('biz_purchase_order_lines', sa.Column('po_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_purchase_order_lines_po_id', 'biz_purchase_order_lines', 'biz_purchase_orders', ['po_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_purchase_order_lines_po_id', 'biz_purchase_order_lines', ['po_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
