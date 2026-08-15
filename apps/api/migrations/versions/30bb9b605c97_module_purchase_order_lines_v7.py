"""module purchase_order_lines v7

Revision ID: 30bb9b605c97
Revises: 87c6143c97a1
Create Date: 2026-08-12T09:08:42.411389+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "30bb9b605c97"
down_revision = '87c6143c97a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_order_lines', sa.Column('item_ref', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_items.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
