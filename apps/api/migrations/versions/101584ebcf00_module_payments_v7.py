"""module payments v7

Revision ID: 101584ebcf00
Revises: fd224b504858
Create Date: 2026-08-13T09:01:15.590011+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "101584ebcf00"
down_revision = 'fd224b504858'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_payments', sa.Column('status', sa.String(length=255), nullable=False, server_default='draft'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
