"""module goods_receipt_lines v2

Revision ID: 11968a42e34f
Revises: ddecdbb9c9b3
Create Date: 2026-08-13T13:46:06.809216+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "11968a42e34f"
down_revision = 'ddecdbb9c9b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_goods_receipt_lines', sa.Column('description', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
