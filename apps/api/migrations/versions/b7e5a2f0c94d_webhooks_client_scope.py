"""webhooks: add client_code column for tenant scoping.

Webhook had no client_code at all: list_webhooks returned every tenant's
webhooks, delete_webhook let any admin delete any other tenant's webhook
by id, and repository._fire_webhooks fired ALL webhooks registered for a
module regardless of which tenant's record changed — leaking one org's
record payloads to another org's registered endpoint. NULL client_code is
treated as legacy/global, same pattern as Clearing/ApprovalRule/SavedView.

Revision ID: b7e5a2f0c94d
Revises: a1c4e9f2b8d3
Create Date: 2026-08-14T00:05:00+00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "b7e5a2f0c94d"
down_revision = "a1c4e9f2b8d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "webhooks",
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), nullable=True),
    )
    op.create_index("ix_webhooks_client_code", "webhooks", ["client_code"])


def downgrade() -> None:
    op.drop_index("ix_webhooks_client_code", table_name="webhooks")
    op.drop_column("webhooks", "client_code")
