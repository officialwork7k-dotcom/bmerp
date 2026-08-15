"""module purchase_orders v21

Revision ID: 35c59f612fc0
Revises: 8664625d9b00
Create Date: 2026-08-14T15:53:07.048150+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "35c59f612fc0"
down_revision = '8664625d9b00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_orders', sa.Column('currency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_currencies.id'), nullable=True))
    op.add_column('biz_purchase_orders', sa.Column('incoterms', sa.String(length=255), nullable=True))
    op.add_column('biz_purchase_orders', sa.Column('requested_delivery_date', sa.Date(), nullable=True))
    op.add_column('biz_purchase_orders', sa.Column('vendor_reference', sa.String(length=255), nullable=True))
    op.add_column('biz_purchase_orders', sa.Column('buyer', sa.String(length=255), nullable=True))
    op.add_column('biz_purchase_orders', sa.Column('header_notes', sa.Text(), nullable=True))
    op.add_column('biz_purchase_orders', sa.Column('tax_total', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_purchase_orders', sa.Column('grand_total', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
