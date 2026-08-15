"""module bank_transactions v1

Revision ID: 0760c4258010
Revises: 5ad0596fc2bc
Create Date: 2026-08-13T09:22:18.584517+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0760c4258010"
down_revision = '5ad0596fc2bc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_bank_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_bank_accounts.id'), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('reconciled', sa.Boolean(), nullable=True, server_default='false'),
    )
    op.create_index('ix_biz_bank_transactions_client_code', 'biz_bank_transactions', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
