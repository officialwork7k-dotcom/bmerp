"""module freshtest v1

Revision ID: 09b4689b1366
Revises: f0213469b980
Create Date: 2026-08-14T16:03:21.994963+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "09b4689b1366"
down_revision = 'f0213469b980'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_freshtest',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('a', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_biz_freshtest_client_code', 'biz_freshtest', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
