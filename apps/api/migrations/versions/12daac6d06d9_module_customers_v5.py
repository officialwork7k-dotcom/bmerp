"""module customers v5

Revision ID: 12daac6d06d9
Revises: aa9a17d880c4
Create Date: 2026-08-14T15:52:16.600922+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "12daac6d06d9"
down_revision = 'aa9a17d880c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_customers', sa.Column('customer_number', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('search_term', sa.String(length=20), nullable=True))
    op.add_column('biz_customers', sa.Column('industry', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('website', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('biz_customers', sa.Column('contact_person', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('contact_phone', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('contact_email', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('postal_code', sa.String(length=20), nullable=True))
    op.add_column('biz_customers', sa.Column('state_region', sa.String(length=100), nullable=True))
    op.add_column('biz_customers', sa.Column('shipping_line1', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('shipping_city', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('shipping_postal_code', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('shipping_country', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('default_currency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_currencies.id'), nullable=True))
    op.add_column('biz_customers', sa.Column('incoterms', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('credit_hold', sa.Boolean(), nullable=True))
    op.add_column('biz_customers', sa.Column('default_salesperson', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('vat_registration_number', sa.String(length=255), nullable=True))
    op.add_column('biz_customers', sa.Column('dunning_enabled', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('biz_customers', sa.Column('tax_exempt', sa.Boolean(), nullable=True))
    op.add_column('biz_customers', sa.Column('tax_exempt_certificate', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
