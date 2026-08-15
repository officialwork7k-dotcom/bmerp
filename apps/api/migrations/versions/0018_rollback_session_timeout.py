"""Rollback: drops `session_timeout_minutes` from localization_settings.

The inactivity-timeout feature (Localization Settings config + sliding
Valkey session TTL) was rolled back — Valkey isn't running in this
environment, so the feature had no real effect and was adding an extra
Postgres round trip to every authenticated request for nothing. See
deps.py/cache.py/auth.py history for the corresponding code revert.

Revision ID: 0018
Revises: 9a61c8a3256c
Create Date: 2026-08-14T00:00:00+00:00
"""
from alembic import op

revision = "0018"
down_revision = "9a61c8a3256c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("biz_localization_settings", "session_timeout_minutes")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column(
        "biz_localization_settings",
        sa.Column("session_timeout_minutes", sa.Integer(), server_default="480", nullable=False),
    )
