"""module opening_balances v1

Revision ID: af20f996f922
Revises: 594aa23b0f11
Create Date: 2026-08-13T18:46:43.532234+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "af20f996f922"
down_revision = '594aa23b0f11'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_opening_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('scope', sa.String(length=255), nullable=False, server_default='GL_ACCOUNT'),
        sa.Column('gl_account_code', sa.String(length=64), nullable=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendors.id'), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_customers.id'), nullable=True),
        sa.Column('amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
    )
    op.create_index('ix_biz_opening_balances_client_code', 'biz_opening_balances', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
