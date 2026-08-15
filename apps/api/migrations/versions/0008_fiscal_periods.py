"""Fiscal periods (one calendar-month posting period per client) + the
period-gate mechanism (see infrastructure/fiscal.py and
FieldMetadata.is_period_gate). Seeds 12 open periods for calendar-year 2026
for the default ORG1 client so a period-gated module works out of the box;
new clients/years are managed via /admin/fiscal-periods.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_SEED_YEAR = 2026
_SEED_CLIENT = "ORG1"


def upgrade() -> None:
    op.create_table(
        "fiscal_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), nullable=False),
        sa.Column("period_key", sa.String(length=7), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="open", nullable=False),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("client_code", "period_key", name="uq_fiscal_periods_client_period"),
    )
    conn = op.get_bind()
    client_exists = conn.execute(sa.text("SELECT 1 FROM clients WHERE code = :c"), {"c": _SEED_CLIENT}).first()
    if client_exists:
        import calendar

        rows = []
        for month in range(1, 13):
            last_day = calendar.monthrange(_SEED_YEAR, month)[1]
            rows.append(
                {
                    "client": _SEED_CLIENT,
                    "period_key": f"{_SEED_YEAR}-{month:02d}",
                    "start": f"{_SEED_YEAR}-{month:02d}-01",
                    "end": f"{_SEED_YEAR}-{month:02d}-{last_day:02d}",
                }
            )
        conn.execute(
            sa.text(
                "INSERT INTO fiscal_periods (client_code, period_key, start_date, end_date, status) "
                "VALUES (:client, :period_key, :start, :end, 'open')"
            ),
            rows,
        )


def downgrade() -> None:
    op.drop_table("fiscal_periods")
