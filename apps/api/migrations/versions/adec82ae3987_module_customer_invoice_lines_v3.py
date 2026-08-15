"""module customer_invoice_lines v3

Revision ID: adec82ae3987
Revises: 2fa736416883
Create Date: 2026-08-13T12:00:22.715821+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "adec82ae3987"
down_revision = '2fa736416883'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('biz_customer_invoice_lines', 'description', nullable=True)


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
