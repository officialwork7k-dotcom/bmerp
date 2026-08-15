"""saved_views: add client_code column for tenant scoping.

SavedView had no client_code at all, so shared (user_id IS NULL) views
leaked across every org using the same module, and delete_view's
ownership check was skipped entirely for shared views. See
infrastructure/repository.py's _validate_lookup_scope and the Clearing
model for the same nullable-client_code pattern (NULL = legacy/global,
matching ApprovalRule).

Revision ID: a1c4e9f2b8d3
Revises: fba18dbb96ed
Create Date: 2026-08-14T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "a1c4e9f2b8d3"
down_revision = "fba18dbb96ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "saved_views",
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), nullable=True),
    )
    op.create_index("ix_saved_views_client_code", "saved_views", ["client_code"])


def downgrade() -> None:
    op.drop_index("ix_saved_views_client_code", table_name="saved_views")
    op.drop_column("saved_views", "client_code")
