"""module deliveries v8

Revision ID: e79cf2b2eac6
Revises: 048efae70eb0
Create Date: 2026-08-14T15:54:03.295149+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e79cf2b2eac6"
down_revision = '048efae70eb0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_deliveries', sa.Column('tracking_number', sa.String(length=255), nullable=True))
    op.add_column('biz_deliveries', sa.Column('carrier', sa.String(length=255), nullable=True))
    op.add_column('biz_deliveries', sa.Column('picked_by', sa.String(length=255), nullable=True))
    op.add_column('biz_deliveries', sa.Column('ship_to_address', sa.String(length=255), nullable=True))
    op.add_column('biz_deliveries', sa.Column('ship_to_city', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
