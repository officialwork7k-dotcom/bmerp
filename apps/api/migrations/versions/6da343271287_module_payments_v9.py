"""module payments v9

Revision ID: 6da343271287
Revises: 8000347bec9d
Create Date: 2026-08-13T19:48:02.385103+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "6da343271287"
down_revision = '8000347bec9d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_payments', sa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_bank_accounts.id'), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
