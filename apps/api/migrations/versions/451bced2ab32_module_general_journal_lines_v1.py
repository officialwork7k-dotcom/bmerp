"""module general_journal_lines v1

Revision ID: 451bced2ab32
Revises: 4c97ad223bc6
Create Date: 2026-08-13T08:54:41.918409+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "451bced2ab32"
down_revision = '4c97ad223bc6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_general_journal_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('account_code', sa.String(length=20), nullable=False),
        sa.Column('account_name', sa.String(length=128), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('debit', sa.Numeric(18, 4), nullable=True, server_default='0'),
        sa.Column('credit', sa.Numeric(18, 4), nullable=True, server_default='0'),
    )
    op.create_index('ix_biz_general_journal_lines_client_code', 'biz_general_journal_lines', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
