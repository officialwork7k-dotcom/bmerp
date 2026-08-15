"""module vendors v8

Revision ID: 0174fd7b19b1
Revises: 5fec3041c9ef
Create Date: 2026-08-13T19:48:00.389246+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0174fd7b19b1"
down_revision = '5fec3041c9ef'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendors', sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_vendor_categories.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
