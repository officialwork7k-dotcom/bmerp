"""module fixed_assets v7

Revision ID: d249e935bdcf
Revises: 09b4689b1366
Create Date: 2026-08-14T17:02:22.669512+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d249e935bdcf"
down_revision = '09b4689b1366'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_fixed_assets', sa.Column('disposal_date', sa.Date(), nullable=True))
    op.add_column('biz_fixed_assets', sa.Column('disposal_proceeds', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
