"""module vendor_invoice_lines v7

Revision ID: ca09eb37ff0e
Revises: 5be5c85e1b47
Create Date: 2026-08-13T11:09:03.476199+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ca09eb37ff0e"
down_revision = '5be5c85e1b47'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendor_invoice_lines', sa.Column('item', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_items.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
