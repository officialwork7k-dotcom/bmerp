"""module vendors v9

Revision ID: aa9a17d880c4
Revises: f5e7fe41abf3
Create Date: 2026-08-14T15:51:49.582613+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "aa9a17d880c4"
down_revision = 'f5e7fe41abf3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_vendors', sa.Column('vendor_number', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('search_term', sa.String(length=20), nullable=True))
    op.add_column('biz_vendors', sa.Column('industry', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('website', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('biz_vendors', sa.Column('contact_person', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('contact_phone', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('contact_email', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('postal_code', sa.String(length=20), nullable=True))
    op.add_column('biz_vendors', sa.Column('state_region', sa.String(length=100), nullable=True))
    op.add_column('biz_vendors', sa.Column('default_currency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_currencies.id'), nullable=True))
    op.add_column('biz_vendors', sa.Column('incoterms', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('purchasing_blocked', sa.Boolean(), nullable=True))
    op.add_column('biz_vendors', sa.Column('vat_registration_number', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('payment_block', sa.Boolean(), nullable=True))
    op.add_column('biz_vendors', sa.Column('tax_classification_1099', sa.String(length=255), nullable=True))
    op.add_column('biz_vendors', sa.Column('w9_on_file', sa.Boolean(), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
