"""module purchase_orders v7

Revision ID: 099203b60125
Revises: 0003
Create Date: 2026-08-12T20:22:52.130667+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "099203b60125"
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_orders', sa.Column('po_number', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
