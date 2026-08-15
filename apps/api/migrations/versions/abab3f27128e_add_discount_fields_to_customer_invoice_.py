"""add discount fields to customer_invoice_lines v5

Revision ID: abab3f27128e
Revises: 835863eb3391
Create Date: 2026-08-15T10:35:04.346248+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "abab3f27128e"
down_revision = '835863eb3391'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customer_invoice_lines', sa.Column('discount_percent', sa.Numeric(18, 4), nullable=True, server_default='0'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
