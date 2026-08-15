"""Fix a double-quoting bug: several VARCHAR columns were declared with
`server_default="'literal'"` (a Python string that already contains SQL
quote characters) instead of `server_default="literal"`. SQLAlchemy quotes
plain-string server_defaults itself, so the pre-quoted form produced
`DEFAULT '''literal'''` — the *stored* default value ends up being the
9-character string `'literal'`, quote characters included, not the
intended 7-character `literal`. Confirmed live: approval_requests rows
inserted via the ORM (relying on this default) got status = "'pending'",
which `WHERE status = 'pending'` never matches — the pending-approvals
queue silently saw nothing.

Fixes the DEFAULT clause on every affected column and repairs any rows
already corrupted by it.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-12T00:00:00+00:00
"""
from alembic import op

revision = "0004"
down_revision = "37ac6109ef7d"
branch_labels = None
depends_on = None

_FIXES = [
    ("number_series", "prefix", ""),
    ("number_series", "reset_policy", "never"),
    ("number_series", "period_key", ""),
    ("notifications", "body", ""),
    ("approval_requests", "status", "pending"),
]


def upgrade() -> None:
    for table, column, correct_value in _FIXES:
        op.alter_column(table, column, server_default=correct_value)
        # The corrupted value is always the correct one wrapped in an extra
        # pair of single quotes (e.g. "'pending'" instead of "pending") —
        # repair exactly that shape, not a blind rewrite, so a row a user
        # genuinely set to contain quote characters isn't silently mangled.
        corrupted = f"'{correct_value}'"
        sql_escaped_correct = correct_value.replace("'", "''")
        sql_escaped_corrupted = corrupted.replace("'", "''")
        op.execute(
            f"UPDATE {table} SET {column} = '{sql_escaped_correct}' "
            f"WHERE {column} = '{sql_escaped_corrupted}'"
        )


def downgrade() -> None:
    for table, column, correct_value in _FIXES:
        op.alter_column(table, column, server_default=f"'{correct_value}'")
