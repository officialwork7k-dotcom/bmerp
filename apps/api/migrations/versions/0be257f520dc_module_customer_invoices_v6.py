"""module customer_invoices v6

Revision ID: 0be257f520dc
Revises: 311ed3b4c79a
Create Date: 2026-08-13T16:26:56.241297+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0be257f520dc"
down_revision = '311ed3b4c79a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customer_invoices', sa.Column('tax_total', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_customer_invoices', sa.Column('grand_total', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
