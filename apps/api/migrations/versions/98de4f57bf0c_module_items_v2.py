"""module items v2

Revision ID: 98de4f57bf0c
Revises: cc9d8628f6da
Create Date: 2026-08-13T08:59:20.233207+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "98de4f57bf0c"
down_revision = 'cc9d8628f6da'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_items', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('biz_items', sa.Column('uom', sa.String(length=255), nullable=True, server_default='EA'))
    op.add_column('biz_items', sa.Column('standard_cost', sa.Numeric(18, 4), nullable=True, server_default='0'))
    op.add_column('biz_items', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
