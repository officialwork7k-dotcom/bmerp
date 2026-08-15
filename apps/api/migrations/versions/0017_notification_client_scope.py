"""Scope notifications by org.

A notification generated while a multi-client user was working in one org
kept showing (and its `link` kept pointing into) that org even after they
switched to another — clicking it 404s since the linked record isn't
visible from the now-active client. Adds `client_code` so the bell and
unread-count queries can exclude notifications for orgs the user isn't
currently signed into.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-14T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notifications", "client_code")
