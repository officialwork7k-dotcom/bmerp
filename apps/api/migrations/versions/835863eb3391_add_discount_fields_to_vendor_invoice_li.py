"""add discount fields to vendor_invoice_lines v18

Revision ID: 835863eb3391
Revises: f4d8e2a917cc
Create Date: 2026-08-15T10:35:03.677967+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "835863eb3391"
down_revision = 'f4d8e2a917cc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendor_invoice_lines', sa.Column('discount_percent', sa.Numeric(18, 4), nullable=True, server_default='0'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
