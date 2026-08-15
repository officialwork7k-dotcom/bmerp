"""module gl_accounts v3

Revision ID: 115cf89013c4
Revises: 35c59f612fc0
Create Date: 2026-08-14T15:53:14.267533+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "115cf89013c4"
down_revision = '35c59f612fc0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_gl_accounts', sa.Column('account_group', sa.String(length=255), nullable=True))
    op.add_column('biz_gl_accounts', sa.Column('blocked_for_posting', sa.Boolean(), nullable=True))
    op.add_column('biz_gl_accounts', sa.Column('currency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_currencies.id'), nullable=True))
    op.add_column('biz_gl_accounts', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
