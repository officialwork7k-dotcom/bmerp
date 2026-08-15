"""module customer_invoices v4

Revision ID: 363d538552df
Revises: 039813e9abb5
Create Date: 2026-08-13T12:01:13.428126+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "363d538552df"
down_revision = '039813e9abb5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('biz_customer_invoices', 'due_date', nullable=True)


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
