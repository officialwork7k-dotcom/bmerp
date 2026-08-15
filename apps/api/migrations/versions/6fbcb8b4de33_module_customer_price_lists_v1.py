"""module customer_price_lists v1

Revision ID: 6fbcb8b4de33
Revises: 8192537046db
Create Date: 2026-08-13T16:38:56.710030+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "6fbcb8b4de33"
down_revision = '8192537046db'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_customer_price_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_customers.id'), nullable=False),
        sa.Column('item', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_items.id'), nullable=False),
        sa.Column('min_qty', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unit_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('discount_pct', sa.Numeric(18, 4), nullable=True, server_default='0'),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
    )
    op.create_index('ix_biz_customer_price_lists_client_code', 'biz_customer_price_lists', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
