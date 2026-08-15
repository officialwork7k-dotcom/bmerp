"""module sales_orders v1

Revision ID: 7d867102ad7a
Revises: ddbfe330930d
Create Date: 2026-08-13T09:13:30.061033+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7d867102ad7a"
down_revision = 'ddbfe330930d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_sales_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('so_number', sa.String(length=255), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_customers.id'), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False, server_default='draft'),
        sa.Column('subtotal', sa.Numeric(18, 4), nullable=True),
    )
    op.create_index('ix_biz_sales_orders_client_code', 'biz_sales_orders', ['client_code'])
    op.add_column('biz_sales_order_lines', sa.Column('so_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_sales_order_lines_so_id', 'biz_sales_order_lines', 'biz_sales_orders', ['so_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_sales_order_lines_so_id', 'biz_sales_order_lines', ['so_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
