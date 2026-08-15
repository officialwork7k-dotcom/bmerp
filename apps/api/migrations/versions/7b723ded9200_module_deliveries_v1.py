"""module deliveries v1

Revision ID: 7b723ded9200
Revises: e871043d61c4
Create Date: 2026-08-13T09:13:52.116813+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7b723ded9200"
down_revision = 'e871043d61c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('delivery_number', sa.String(length=255), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_customers.id'), nullable=False),
        sa.Column('so_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_sales_orders.id'), nullable=True),
        sa.Column('delivery_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False, server_default='draft'),
    )
    op.create_index('ix_biz_deliveries_client_code', 'biz_deliveries', ['client_code'])
    op.add_column('biz_delivery_lines', sa.Column('delivery_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_biz_delivery_lines_delivery_id', 'biz_delivery_lines', 'biz_deliveries', ['delivery_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_biz_delivery_lines_delivery_id', 'biz_delivery_lines', ['delivery_id'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
