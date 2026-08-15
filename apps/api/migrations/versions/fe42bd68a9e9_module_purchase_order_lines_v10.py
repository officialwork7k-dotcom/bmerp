"""module purchase_order_lines v10

Revision ID: fe42bd68a9e9
Revises: 27e63ef47d2a
Create Date: 2026-08-13T16:25:55.837930+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "fe42bd68a9e9"
down_revision = '27e63ef47d2a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_order_lines', sa.Column('tax_code_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_tax_codes.id'), nullable=True))
    op.add_column('biz_purchase_order_lines', sa.Column('tax_rate', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_purchase_order_lines', sa.Column('tax_amount', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
