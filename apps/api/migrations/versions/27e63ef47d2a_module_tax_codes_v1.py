"""module tax_codes v1

Revision ID: 27e63ef47d2a
Revises: 65d41e72eed2
Create Date: 2026-08-13T16:24:43.606169+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "27e63ef47d2a"
down_revision = '65d41e72eed2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_tax_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=128), nullable=True),
        sa.Column('rate', sa.Numeric(18, 4), nullable=False),
        sa.Column('gl_account_code', sa.String(length=20), nullable=False),
        sa.Column('gl_account_name', sa.String(length=128), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
    )
    op.create_index('ix_biz_tax_codes_client_code', 'biz_tax_codes', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
