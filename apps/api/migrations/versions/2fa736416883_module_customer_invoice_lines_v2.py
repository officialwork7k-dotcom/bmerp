"""module customer_invoice_lines v2

Revision ID: 2fa736416883
Revises: 71476f37d68f
Create Date: 2026-08-13T12:00:21.499125+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "2fa736416883"
down_revision = '71476f37d68f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customer_invoice_lines', sa.Column('item', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_items.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
