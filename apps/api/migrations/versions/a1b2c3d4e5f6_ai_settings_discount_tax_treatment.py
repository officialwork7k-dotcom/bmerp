"""Adds AiSettings.discount_tax_treatment — governs whether the chat
assistant's system prompt instructs it to record a scanned document's
discount as pre-tax (line-level discount_percent, nets out of line_total
before tax_amount computes from it — standard invoicing practice) or
post-tax (header-level discount_amount, subtracted from grand_total after
tax_total). Defaults to 'before_tax'. See infrastructure/models.py's
AiSettings.discount_tax_treatment docstring for the full incident this was
added to fix.

Revision ID: a1b2c3d4e5f6
Revises: 60ad73e984a2
Create Date: 2026-08-16T00:00:00+00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "60ad73e984a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_settings",
        sa.Column("discount_tax_treatment", sa.String(16), nullable=False, server_default="before_tax"),
    )


def downgrade() -> None:
    op.drop_column("ai_settings", "discount_tax_treatment")
