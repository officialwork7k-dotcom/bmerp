"""add discount fields to customer_invoices v15

Revision ID: 60ad73e984a2
Revises: 28c33398caa9
Create Date: 2026-08-15T10:35:04.996074+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "60ad73e984a2"
down_revision = '28c33398caa9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customer_invoices', sa.Column('discount_amount', sa.Numeric(18, 4), nullable=True, server_default='0'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
