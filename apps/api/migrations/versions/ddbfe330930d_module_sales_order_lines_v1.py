"""module sales_order_lines v1

Revision ID: ddbfe330930d
Revises: 101584ebcf00
Create Date: 2026-08-13T09:13:28.015550+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ddbfe330930d"
down_revision = '101584ebcf00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_sales_order_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('item', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_items.id'), nullable=False),
        sa.Column('qty', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('line_total', sa.Numeric(18, 4), nullable=True),
    )
    op.create_index('ix_biz_sales_order_lines_client_code', 'biz_sales_order_lines', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
