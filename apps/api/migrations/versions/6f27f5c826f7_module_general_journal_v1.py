"""module general_journal v1

Revision ID: 6f27f5c826f7
Revises: 451bced2ab32
Create Date: 2026-08-13T08:55:05.721810+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "6f27f5c826f7"
down_revision = '451bced2ab32'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_general_journal',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('doc_number', sa.String(length=255), nullable=True),
        sa.Column('doc_date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=False, server_default='draft'),
    )
    op.create_index('ix_biz_general_journal_client_code', 'biz_general_journal', ['client_code'])
    op.add_column('biz_general_journal_lines', sa.Column('journal_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_general_journal_lines_journal_id', 'biz_general_journal_lines', 'biz_general_journal', ['journal_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_general_journal_lines_journal_id', 'biz_general_journal_lines', ['journal_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
