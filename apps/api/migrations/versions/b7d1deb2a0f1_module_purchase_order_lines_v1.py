"""module purchase_order_lines v1

Revision ID: b7d1deb2a0f1
Revises: c9625bf10e3b
Create Date: 2026-08-12T06:09:13.609343+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b7d1deb2a0f1"
down_revision = 'c9625bf10e3b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_purchase_order_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('item', sa.String(length=255), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('line_total', sa.Numeric(18, 4), nullable=True),
    )


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
