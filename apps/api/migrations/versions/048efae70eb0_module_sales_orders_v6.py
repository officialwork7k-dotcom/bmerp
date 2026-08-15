"""module sales_orders v6

Revision ID: 048efae70eb0
Revises: 50c7b8e8aa1e
Create Date: 2026-08-14T15:53:56.439467+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "048efae70eb0"
down_revision = '50c7b8e8aa1e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_sales_orders', sa.Column('currency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_currencies.id'), nullable=True))
    op.add_column('biz_sales_orders', sa.Column('incoterms', sa.String(length=255), nullable=True))
    op.add_column('biz_sales_orders', sa.Column('requested_delivery_date', sa.Date(), nullable=True))
    op.add_column('biz_sales_orders', sa.Column('customer_po_reference', sa.String(length=255), nullable=True))
    op.add_column('biz_sales_orders', sa.Column('salesperson', sa.String(length=255), nullable=True))
    op.add_column('biz_sales_orders', sa.Column('priority', sa.String(length=255), nullable=True, server_default='normal'))
    op.add_column('biz_sales_orders', sa.Column('header_notes', sa.Text(), nullable=True))
    op.add_column('biz_sales_orders', sa.Column('tax_total', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_sales_orders', sa.Column('grand_total', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
