"""module items v3

Revision ID: 65d41e72eed2
Revises: 53af5a833b29
Create Date: 2026-08-13T13:52:10.342992+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "65d41e72eed2"
down_revision = '53af5a833b29'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_items', sa.Column('item_type', sa.String(length=255), nullable=False, server_default='STOCK'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
