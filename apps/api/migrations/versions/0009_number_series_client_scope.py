"""Number ranges gain a client_code dimension: without this, every tenant
shared one global AUTO_NUMBER counter per (module, field, period) — a real
cross-tenant leak introduced once client tenancy (0006) added multiple
clients to a single install. Existing rows backfill to 'ORG1', matching
every other 0006-era backfill.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_DEFAULT_CLIENT = "ORG1"


def upgrade() -> None:
    op.add_column(
        "number_series",
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), server_default=_DEFAULT_CLIENT, nullable=False),
    )
    op.drop_constraint("uq_number_series_module_field_period", "number_series", type_="unique")
    op.create_unique_constraint(
        "uq_number_series_client_module_field_period", "number_series", ["client_code", "module", "field", "period_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_number_series_client_module_field_period", "number_series", type_="unique")
    op.create_unique_constraint("uq_number_series_module_field_period", "number_series", ["module", "field", "period_key"])
    op.drop_column("number_series", "client_code")
