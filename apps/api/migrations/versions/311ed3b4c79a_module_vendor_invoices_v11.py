"""module vendor_invoices v11

Revision ID: 311ed3b4c79a
Revises: c3cb57dcb600
Create Date: 2026-08-13T16:26:28.642160+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "311ed3b4c79a"
down_revision = 'c3cb57dcb600'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendor_invoices', sa.Column('tax_total', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_vendor_invoices', sa.Column('grand_total', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
