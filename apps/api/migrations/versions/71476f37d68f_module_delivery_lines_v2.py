"""module delivery_lines v2

Revision ID: 71476f37d68f
Revises: 34c62bd87551
Create Date: 2026-08-13T11:59:56.667374+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "71476f37d68f"
down_revision = '34c62bd87551'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_delivery_lines', sa.Column('unit_price', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
