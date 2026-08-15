"""module purchase_order_lines v9

Revision ID: ddecdbb9c9b3
Revises: 363d538552df
Create Date: 2026-08-13T13:46:05.082565+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ddecdbb9c9b3"
down_revision = '363d538552df'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_purchase_order_lines', sa.Column('description', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
