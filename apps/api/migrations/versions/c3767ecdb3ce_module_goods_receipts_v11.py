"""module goods_receipts v11

Revision ID: c3767ecdb3ce
Revises: 115cf89013c4
Create Date: 2026-08-14T15:53:19.843208+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3767ecdb3ce"
down_revision = '115cf89013c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_goods_receipts', sa.Column('delivery_note_number', sa.String(length=255), nullable=True))
    op.add_column('biz_goods_receipts', sa.Column('received_by', sa.String(length=255), nullable=True))
    op.add_column('biz_goods_receipts', sa.Column('posting_date', sa.Date(), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
