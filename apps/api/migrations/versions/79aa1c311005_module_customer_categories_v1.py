"""module customer_categories v1

Revision ID: 79aa1c311005
Revises: 78024448452e
Create Date: 2026-08-13T19:46:02.704085+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "79aa1c311005"
down_revision = '78024448452e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_customer_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('ar_gl_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_gl_accounts.id'), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_biz_customer_categories_client_code', 'biz_customer_categories', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
