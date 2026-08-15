"""module localization_settings v3

Revision ID: 9a61c8a3256c
Revises: 0017
Create Date: 2026-08-14T13:12:33.528887+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9a61c8a3256c"
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_localization_settings', sa.Column('session_timeout_minutes', sa.Integer(), nullable=False, server_default='480'))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
