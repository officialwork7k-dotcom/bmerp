"""module sales_order_lines v3

Revision ID: ad907f28a17e
Revises: a35daf734b3d
Create Date: 2026-08-13T16:25:58.312987+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ad907f28a17e"
down_revision = 'a35daf734b3d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_sales_order_lines', sa.Column('tax_code_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_tax_codes.id'), nullable=True))
    op.add_column('biz_sales_order_lines', sa.Column('tax_rate', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_sales_order_lines', sa.Column('tax_amount', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
