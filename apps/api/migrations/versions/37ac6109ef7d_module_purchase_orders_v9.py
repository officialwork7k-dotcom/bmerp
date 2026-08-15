"""module purchase_orders v9

Revision ID: 37ac6109ef7d
Revises: 0bad11d287f1
Create Date: 2026-08-12T20:26:39.489830+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "37ac6109ef7d"
down_revision = '0bad11d287f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_orders', sa.Column('po_num', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
