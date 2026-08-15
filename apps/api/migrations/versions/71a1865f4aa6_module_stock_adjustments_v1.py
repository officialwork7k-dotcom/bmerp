"""module stock_adjustments v1

Revision ID: 71a1865f4aa6
Revises: 5107a67140f2
Create Date: 2026-08-14T06:23:13.762472+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "71a1865f4aa6"
down_revision = '5107a67140f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_stock_adjustments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('adjustment_number', sa.String(length=255), nullable=True),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_items.id'), nullable=False),
        sa.Column('movement_type', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit_cost', sa.Numeric(18, 4), nullable=True),
        sa.Column('adjustment_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=False, server_default='draft'),
    )
    op.create_index('ix_biz_stock_adjustments_client_code', 'biz_stock_adjustments', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
