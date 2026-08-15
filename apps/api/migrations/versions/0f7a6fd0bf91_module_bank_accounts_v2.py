"""module bank_accounts v2

Revision ID: 0f7a6fd0bf91
Revises: 862f5910f417
Create Date: 2026-08-14T15:54:27.476862+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0f7a6fd0bf91"
down_revision = '862f5910f417'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_bank_accounts', sa.Column('currency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_currencies.id'), nullable=True))
    op.add_column('biz_bank_accounts', sa.Column('iban', sa.String(length=255), nullable=True))
    op.add_column('biz_bank_accounts', sa.Column('swift_bic', sa.String(length=255), nullable=True))
    op.add_column('biz_bank_accounts', sa.Column('bank_branch', sa.String(length=255), nullable=True))
    op.add_column('biz_bank_accounts', sa.Column('bank_address', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
