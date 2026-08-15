"""module delivery_lines v3

Revision ID: 53af5a833b29
Revises: e88af4d77bc2
Create Date: 2026-08-13T13:46:09.484864+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "53af5a833b29"
down_revision = 'e88af4d77bc2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_delivery_lines', sa.Column('description', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
