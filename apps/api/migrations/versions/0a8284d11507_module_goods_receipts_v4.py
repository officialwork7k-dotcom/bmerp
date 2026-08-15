"""module goods_receipts v4

Revision ID: 0a8284d11507
Revises: 922c6baa6a2b
Create Date: 2026-08-13T16:35:04.742843+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0a8284d11507"
down_revision = '922c6baa6a2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_goods_receipts', sa.Column('total_charges', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_goods_receipt_charges', sa.Column('gr_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_goods_receipt_charges_gr_id', 'biz_goods_receipt_charges', 'biz_goods_receipts', ['gr_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_goods_receipt_charges_gr_id', 'biz_goods_receipt_charges', ['gr_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
