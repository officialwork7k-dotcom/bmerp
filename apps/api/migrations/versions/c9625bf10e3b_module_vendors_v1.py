"""module vendors v1

Revision ID: c9625bf10e3b
Revises: 2fbfed49184d
Create Date: 2026-08-12T06:09:10.191149+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c9625bf10e3b"
down_revision = '2fbfed49184d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_vendors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=255), nullable=True),
        sa.Column('payment_terms', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
