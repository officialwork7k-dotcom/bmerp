"""Approval routing: who approves what.

`approval_rules` answers the question the existing `approval_requests` queue
never could — WHO is allowed to decide a given request. Previously any admin
could decide any pending approval, and the queue was only ever reached when
a user had zero `update` permission on the module (a pure RBAC fallback, not
a business control). This adds real routing: a rule targets a
(module, to_status) transition, requires sign-off from a specific role, and
can optionally be gated by an amount threshold read off the record itself
(tiered approval — small documents post straight through, large ones need a
manager). `client_code` NULL means the rule is global (every tenant);
setting it scopes a rule to one org, matching how the rest of the framework
scopes config.

Also adds `client_code` to `approval_requests` (nullable, backfilled from
the requester's own client) so a request from one org never surfaces in
another org's approval queue.

Revision ID: 0016
Revises: 71a1865f4aa6
Create Date: 2026-08-14T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "71a1865f4aa6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), nullable=True),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("to_status", sa.String(length=64), nullable=False),
        sa.Column("approver_role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount_field", sa.String(length=64), nullable=True),
        sa.Column("min_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "approval_requests",
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("approval_requests", "client_code")
    op.drop_table("approval_rules")
