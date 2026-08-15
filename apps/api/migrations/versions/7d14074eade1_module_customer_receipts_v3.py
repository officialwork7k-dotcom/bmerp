"""module customer_receipts v3

Revision ID: 7d14074eade1
Revises: 6da343271287
Create Date: 2026-08-13T19:48:03.312664+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7d14074eade1"
down_revision = '6da343271287'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customer_receipts', sa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_bank_accounts.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
