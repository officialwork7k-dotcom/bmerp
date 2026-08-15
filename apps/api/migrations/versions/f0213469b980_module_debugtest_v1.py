"""module debugtest v1

Revision ID: f0213469b980
Revises: 01e952b59647
Create Date: 2026-08-14T16:02:28.142635+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f0213469b980"
down_revision = '01e952b59647'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_debugtest',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('a', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_biz_debugtest_client_code', 'biz_debugtest', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
