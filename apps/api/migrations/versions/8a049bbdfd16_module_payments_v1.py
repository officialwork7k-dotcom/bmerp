"""module payments v1

Revision ID: 8a049bbdfd16
Revises: 619bad4bb452
Create Date: 2026-08-12T06:09:25.108311+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8a049bbdfd16"
down_revision = '619bad4bb452'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendors.id'), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendor_invoices.id'), nullable=False),
        sa.Column('amount', sa.Numeric(18, 4), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('method', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
