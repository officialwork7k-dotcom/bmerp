"""module items v4

Revision ID: 8664625d9b00
Revises: 12daac6d06d9
Create Date: 2026-08-14T15:52:28.014283+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8664625d9b00"
down_revision = '12daac6d06d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_items', sa.Column('item_group', sa.String(length=255), nullable=True))
    op.add_column('biz_items', sa.Column('barcode_ean', sa.String(length=255), nullable=True))
    op.add_column('biz_items', sa.Column('manufacturer_part_number', sa.String(length=255), nullable=True))
    op.add_column('biz_items', sa.Column('is_purchasable', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('biz_items', sa.Column('is_sellable', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('biz_items', sa.Column('is_stocked', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('biz_items', sa.Column('weight', sa.Numeric(18, 3), nullable=True))
    op.add_column('biz_items', sa.Column('weight_uom', sa.String(length=255), nullable=True))
    op.add_column('biz_items', sa.Column('sales_price', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_items', sa.Column('sales_tax_code_default', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_tax_codes.id'), nullable=True))
    op.add_column('biz_items', sa.Column('purchase_tax_code_default', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_tax_codes.id'), nullable=True))
    op.add_column('biz_items', sa.Column('default_vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendors.id'), nullable=True))
    op.add_column('biz_items', sa.Column('lead_time_days', sa.Integer(), nullable=True))
    op.add_column('biz_items', sa.Column('reorder_point', sa.Numeric(18, 2), nullable=True))
    op.add_column('biz_items', sa.Column('min_stock_level', sa.Numeric(18, 2), nullable=True))
    op.add_column('biz_items', sa.Column('max_stock_level', sa.Numeric(18, 2), nullable=True))
    op.add_column('biz_items', sa.Column('shelf_location', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
