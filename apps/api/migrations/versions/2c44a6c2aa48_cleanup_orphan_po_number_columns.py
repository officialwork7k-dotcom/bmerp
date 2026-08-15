"""cleanup orphan po_number columns

Revision ID: 2c44a6c2aa48
Revises: 3385fd1945ad
Create Date: 2026-08-13 15:24:08.541989
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '2c44a6c2aa48'
down_revision = '3385fd1945ad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Orphaned columns from repeated failed builder-API attempts to add a
    # po_number field: each attempt's DDL committed independently of the
    # module-metadata row update, so the columns landed without ever being
    # reflected in module metadata. Dropping them so the field can be added
    # cleanly through the normal builder flow.
    op.drop_column('biz_purchase_orders', 'po_number')
    op.drop_column('biz_purchase_orders', 'po_no')
    op.drop_column('biz_purchase_orders', 'po_num')


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
