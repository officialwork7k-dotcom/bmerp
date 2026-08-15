"""module goods_receipt_lines v3

Revision ID: 9c205a091827
Revises: 6fbcb8b4de33
Create Date: 2026-08-13T17:18:22.855599+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9c205a091827"
down_revision = '6fbcb8b4de33'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_goods_receipt_lines', sa.Column('tax_code_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_tax_codes.id'), nullable=True))
    op.add_column('biz_goods_receipt_lines', sa.Column('tax_rate', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
