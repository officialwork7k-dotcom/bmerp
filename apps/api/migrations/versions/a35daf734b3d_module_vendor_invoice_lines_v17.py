"""module vendor_invoice_lines v17

Revision ID: a35daf734b3d
Revises: fe42bd68a9e9
Create Date: 2026-08-13T16:25:57.093361+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a35daf734b3d"
down_revision = 'fe42bd68a9e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendor_invoice_lines', sa.Column('tax_code_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_tax_codes.id'), nullable=True))
    op.add_column('biz_vendor_invoice_lines', sa.Column('tax_rate', sa.Numeric(18, 4), nullable=True))
    op.add_column('biz_vendor_invoice_lines', sa.Column('tax_amount', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
