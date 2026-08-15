"""module purchase_orders v8

Revision ID: 0bad11d287f1
Revises: 099203b60125
Create Date: 2026-08-12T20:25:48.872676+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0bad11d287f1"
down_revision = '099203b60125'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_orders', sa.Column('po_no', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
