"""module fixed_assets v1

Revision ID: 5be5c85e1b47
Revises: 0760c4258010
Create Date: 2026-08-13T09:22:39.556314+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "5be5c85e1b47"
down_revision = '0760c4258010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_fixed_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('asset_code', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=False),
        sa.Column('acquisition_date', sa.Date(), nullable=False),
        sa.Column('acquisition_cost', sa.Numeric(18, 4), nullable=False),
        sa.Column('salvage_value', sa.Numeric(18, 4), nullable=True, server_default='0'),
        sa.Column('useful_life_months', sa.Integer(), nullable=False),
        sa.Column('accumulated_depreciation', sa.Numeric(18, 4), nullable=True, server_default='0'),
        sa.Column('gl_asset_account', sa.String(length=20), nullable=True, server_default='1500'),
        sa.Column('gl_depreciation_expense_account', sa.String(length=20), nullable=True, server_default='6100'),
        sa.Column('gl_accum_depreciation_account', sa.String(length=20), nullable=True, server_default='1510'),
        sa.Column('status', sa.String(length=255), nullable=False, server_default='active'),
    )
    op.create_index('ix_biz_fixed_assets_client_code', 'biz_fixed_assets', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
