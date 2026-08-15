"""module vendors v7

Revision ID: 02fdaf1a1b0e
Revises: 6f27f5c826f7
Create Date: 2026-08-13T08:55:40.126984+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "02fdaf1a1b0e"
down_revision = '6f27f5c826f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendors', sa.Column('tax_id', sa.String(length=32), nullable=True))
    op.add_column('biz_vendors', sa.Column('address_line1', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('city', sa.String(length=128), nullable=True))
    op.add_column('biz_vendors', sa.Column('country', sa.String(length=128), nullable=True))
    op.add_column('biz_vendors', sa.Column('bank_account', sa.String(length=64), nullable=True))
    op.add_column('biz_vendors', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
