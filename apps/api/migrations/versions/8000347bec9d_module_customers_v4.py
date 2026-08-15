"""module customers v4

Revision ID: 8000347bec9d
Revises: 0174fd7b19b1
Create Date: 2026-08-13T19:48:01.395937+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "8000347bec9d"
down_revision = '0174fd7b19b1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customers', sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_customer_categories.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
