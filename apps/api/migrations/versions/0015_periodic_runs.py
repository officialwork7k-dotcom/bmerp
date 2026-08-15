"""Synchronous idempotent periodic run pattern: `periodic_runs` log table —
see infrastructure/periodic_runs.py. Explicitly no ARQ dependency (the
known ARQ hang problem was descoped for phase 1) — this is a plain HTTP-
request-synchronous pattern, gated by a partial unique index so a
completed run for a given (client, run_type, period) can never happen
twice, the same partial-unique-index technique already used for
FieldMetadata.is_default_flag.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "periodic_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), nullable=True),
        sa.Column("run_type", sa.String(length=64), nullable=False),
        sa.Column("period_key", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="running", nullable=False),
        sa.Column("result_summary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Partial: only a COMPLETED run blocks a re-run of the same period — a
    # failed attempt must not permanently lock a period out of ever being
    # retried.
    op.execute(
        "CREATE UNIQUE INDEX uq_periodic_runs_completed "
        "ON periodic_runs (client_code, run_type, period_key) "
        "WHERE status = 'completed'"
    )


def downgrade() -> None:
    op.drop_table("periodic_runs")
