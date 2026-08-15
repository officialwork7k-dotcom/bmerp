"""module localization_settings v2

Revision ID: 40878fb18dfe
Revises: 58f9846912f4
Create Date: 2026-08-12T17:54:46.819954+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "40878fb18dfe"
down_revision = '58f9846912f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_localization_settings', sa.Column('profile_name', sa.String(length=255), nullable=False, server_default='Default'))
    op.add_column('biz_localization_settings', sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'))
    op.execute('CREATE UNIQUE INDEX uq_biz_localization_settings_is_default_default ON biz_localization_settings ((true)) WHERE "is_default"')
    op.add_column('biz_localization_settings', sa.Column('time_format', sa.String(length=255), nullable=False, server_default='24-hour'))
    op.add_column('biz_localization_settings', sa.Column('timezone', sa.String(length=255), nullable=False, server_default='UTC'))
    op.add_column('biz_localization_settings', sa.Column('first_day_of_week', sa.String(length=255), nullable=False, server_default='Monday'))
    op.add_column('biz_localization_settings', sa.Column('decimal_separator', sa.String(length=255), nullable=False, server_default='.'))
    op.add_column('biz_localization_settings', sa.Column('thousands_separator', sa.String(length=255), nullable=False, server_default=','))
    op.add_column('biz_localization_settings', sa.Column('currency_symbol_position', sa.String(length=255), nullable=False, server_default='before'))
    op.add_column('biz_localization_settings', sa.Column('negative_number_format', sa.String(length=255), nullable=False, server_default='-1,234.56'))
    op.add_column('biz_localization_settings', sa.Column('fiscal_year_start_month', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('biz_localization_settings', sa.Column('notification_position', sa.String(length=255), nullable=False, server_default='bottom-center'))
    op.add_column('biz_localization_settings', sa.Column('notification_duration_seconds', sa.Integer(), nullable=False, server_default='4'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
