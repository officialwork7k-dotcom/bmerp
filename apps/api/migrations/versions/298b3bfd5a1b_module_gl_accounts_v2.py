"""module gl_accounts v2

Revision ID: 298b3bfd5a1b
Revises: 7d14074eade1
Create Date: 2026-08-14T06:03:07.030552+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "298b3bfd5a1b"
down_revision = '7d14074eade1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_gl_accounts', sa.Column('is_reconciliation_account', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
