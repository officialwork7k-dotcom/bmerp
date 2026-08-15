"""module localization_settings v1

Revision ID: 58f9846912f4
Revises: d4f8a1b23c56
Create Date: 2026-08-12T17:09:32.219831+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "58f9846912f4"
down_revision = 'd4f8a1b23c56'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_localization_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('date_format', sa.String(length=255), nullable=False),
        sa.Column('currency_code', sa.String(length=255), nullable=False),
        sa.Column('number_format', sa.String(length=255), nullable=False),
    )


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
