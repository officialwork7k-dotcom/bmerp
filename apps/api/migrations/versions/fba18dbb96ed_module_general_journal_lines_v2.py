"""module general_journal_lines v2

Revision ID: fba18dbb96ed
Revises: d249e935bdcf
Create Date: 2026-08-14T17:34:13.775641+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "fba18dbb96ed"
down_revision = 'd249e935bdcf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_general_journal_lines', sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_gl_accounts.id'), nullable=True))
    op.alter_column('biz_general_journal_lines', 'account_code', nullable=True)


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
