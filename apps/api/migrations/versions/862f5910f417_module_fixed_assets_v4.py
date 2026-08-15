"""module fixed_assets v4

Revision ID: 862f5910f417
Revises: 886c7febd75d
Create Date: 2026-08-14T15:54:21.597578+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "862f5910f417"
down_revision = '886c7febd75d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_fixed_assets', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column('biz_fixed_assets', sa.Column('serial_number', sa.String(length=255), nullable=True))
    op.add_column('biz_fixed_assets', sa.Column('custodian', sa.String(length=255), nullable=True))
    op.add_column('biz_fixed_assets', sa.Column('insurance_value', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_fixed_assets', sa.Column('warranty_expiry', sa.Date(), nullable=True))
    op.add_column('biz_fixed_assets', sa.Column('net_book_value', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
