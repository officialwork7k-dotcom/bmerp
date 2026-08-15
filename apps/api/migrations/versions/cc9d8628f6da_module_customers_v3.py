"""module customers v3

Revision ID: cc9d8628f6da
Revises: 02fdaf1a1b0e
Create Date: 2026-08-13T08:55:57.703349+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "cc9d8628f6da"
down_revision = '02fdaf1a1b0e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customers', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('phone', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('payment_terms', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('tax_id', sa.String(length=32), nullable=True))
    op.add_column('biz_customers', sa.Column('credit_limit', sa.Numeric(18, 4), nullable=True, server_default='0'))
    op.add_column('biz_customers', sa.Column('address_line1', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('city', sa.String(length=128), nullable=True))
    op.add_column('biz_customers', sa.Column('country', sa.String(length=128), nullable=True))
    op.add_column('biz_customers', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
