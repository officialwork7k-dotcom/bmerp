"""module purchase_orders v15

Revision ID: e9f2762a6aed
Revises: 2c44a6c2aa48
Create Date: 2026-08-13T11:26:00.083292+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e9f2762a6aed"
down_revision = '2c44a6c2aa48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_orders', sa.Column('po_number', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
