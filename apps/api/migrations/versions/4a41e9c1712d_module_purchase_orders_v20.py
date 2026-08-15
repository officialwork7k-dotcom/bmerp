"""module purchase_orders v20

Revision ID: 4a41e9c1712d
Revises: 1efdf2bc4729
Create Date: 2026-08-13T18:12:31.528308+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "4a41e9c1712d"
down_revision = '1efdf2bc4729'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_orders', sa.Column('total_charges', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_purchase_order_charges', sa.Column('po_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_purchase_order_charges_po_id', 'biz_purchase_order_charges', 'biz_purchase_orders', ['po_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_purchase_order_charges_po_id', 'biz_purchase_order_charges', ['po_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
