"""module sales_order_lines v2

Revision ID: e88af4d77bc2
Revises: 11968a42e34f
Create Date: 2026-08-13T13:46:08.139675+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e88af4d77bc2"
down_revision = '11968a42e34f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_sales_order_lines', sa.Column('description', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
