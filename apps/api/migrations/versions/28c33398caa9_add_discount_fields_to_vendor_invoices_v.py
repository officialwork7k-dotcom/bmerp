"""add discount fields to vendor_invoices v24

Revision ID: 28c33398caa9
Revises: abab3f27128e
Create Date: 2026-08-15T10:35:04.691281+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "28c33398caa9"
down_revision = 'abab3f27128e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendor_invoices', sa.Column('discount_amount', sa.Numeric(18, 4), nullable=True, server_default='0'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
