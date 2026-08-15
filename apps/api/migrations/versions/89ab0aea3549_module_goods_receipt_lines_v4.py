"""module goods_receipt_lines v4

Revision ID: 89ab0aea3549
Revises: c3767ecdb3ce
Create Date: 2026-08-14T15:53:28.352943+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "89ab0aea3549"
down_revision = 'c3767ecdb3ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_goods_receipt_lines', sa.Column('bin_location', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
