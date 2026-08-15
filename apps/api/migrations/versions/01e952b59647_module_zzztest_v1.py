"""module zzztest v1

Revision ID: 01e952b59647
Revises: 0f7a6fd0bf91
Create Date: 2026-08-14T15:57:48.556177+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "01e952b59647"
down_revision = '0f7a6fd0bf91'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_zzztest',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('a', sa.String(length=255), nullable=True),
        sa.Column('b', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_biz_zzztest_client_code', 'biz_zzztest', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
