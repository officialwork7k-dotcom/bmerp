"""module goods_receipt_charges v1

Revision ID: 922c6baa6a2b
Revises: 0be257f520dc
Create Date: 2026-08-13T16:34:44.606840+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "922c6baa6a2b"
down_revision = '0be257f520dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_goods_receipt_charges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('charge_type', sa.String(length=255), nullable=False, server_default='FREIGHT'),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(18, 4), nullable=False),
    )
    op.create_index('ix_biz_goods_receipt_charges_client_code', 'biz_goods_receipt_charges', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
