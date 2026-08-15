"""module currencies v1

Revision ID: f5e7fe41abf3
Revises: adafd7dd7d1b
Create Date: 2026-08-14T15:50:23.959394+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f5e7fe41abf3"
down_revision = 'adafd7dd7d1b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_currencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('code', sa.String(length=3), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=5), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
    )
    op.create_index('ix_biz_currencies_client_code', 'biz_currencies', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
