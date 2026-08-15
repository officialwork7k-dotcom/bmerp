"""module customer_invoices v2

Revision ID: 039813e9abb5
Revises: adec82ae3987
Create Date: 2026-08-13T12:00:36.574797+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "039813e9abb5"
down_revision = 'adec82ae3987'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customer_invoices', sa.Column('delivery_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_deliveries.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
