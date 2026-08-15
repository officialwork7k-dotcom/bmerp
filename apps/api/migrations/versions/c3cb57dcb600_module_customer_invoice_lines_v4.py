"""module customer_invoice_lines v4

Revision ID: c3cb57dcb600
Revises: ad907f28a17e
Create Date: 2026-08-13T16:25:59.553437+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3cb57dcb600"
down_revision = 'ad907f28a17e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customer_invoice_lines', sa.Column('tax_code_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_tax_codes.id'), nullable=True))
    op.add_column('biz_customer_invoice_lines', sa.Column('tax_rate', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_customer_invoice_lines', sa.Column('tax_amount', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
