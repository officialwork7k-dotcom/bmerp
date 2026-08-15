"""module bank_accounts v1

Revision ID: 5ad0596fc2bc
Revises: 32618f2a5fa8
Create Date: 2026-08-13T09:22:16.894655+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "5ad0596fc2bc"
down_revision = '32618f2a5fa8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_bank_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('account_name', sa.String(length=128), nullable=False),
        sa.Column('bank_name', sa.String(length=128), nullable=False),
        sa.Column('account_number', sa.String(length=64), nullable=False),
        sa.Column('gl_account_code', sa.String(length=20), nullable=False, server_default='1000'),
        sa.Column('opening_balance', sa.Numeric(18, 4), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
    )
    op.create_index('ix_biz_bank_accounts_client_code', 'biz_bank_accounts', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
