"""module purchase_order_charges v1

Revision ID: afd2ec838656
Revises: 9c205a091827
Create Date: 2026-08-13T18:12:29.836356+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "afd2ec838656"
down_revision = '9c205a091827'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_purchase_order_charges',
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
    op.create_index('ix_biz_purchase_order_charges_client_code', 'biz_purchase_order_charges', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
