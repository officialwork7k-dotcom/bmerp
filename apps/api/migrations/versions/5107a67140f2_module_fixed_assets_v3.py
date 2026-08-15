"""module fixed_assets v3

Revision ID: 5107a67140f2
Revises: 298b3bfd5a1b
Create Date: 2026-08-14T06:19:26.416978+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "5107a67140f2"
down_revision = '298b3bfd5a1b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_fixed_assets', sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendors.id'), nullable=True))
    op.add_column('biz_fixed_assets', sa.Column('posting_status', sa.String(length=255), nullable=False, server_default='draft'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
