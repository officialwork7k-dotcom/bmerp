"""Repairs `client_code` missing on biz_* tables whose physical CREATE
TABLE predates migration 0006.

0006 discovered "which tables need client_code" via `SELECT name FROM
modules` — correct in an environment where the module registry gets built
up incrementally as each module's table is created (the normal builder
workflow, and how every environment this app had run in until now was
populated), but wrong on a from-scratch deploy: `alembic upgrade head`
runs before any module-registry seed data exists, so `modules` was empty
when 0006's loop ran, and it silently skipped every table that already
existed at that point in the migration chain (vendors, customers,
purchase_order_lines, purchase_orders, vendor_invoice_lines,
vendor_invoices, payments, items, localization_settings — confirmed live
on a fresh deploy: `SELECT * FROM biz_vendors` failed with
`UndefinedColumnError: column biz_vendors.client_code does not exist`).

Fixed here by reflecting the ACTUAL physical schema (information_schema)
instead of the module registry, so it's correct regardless of deploy
order — every biz_* table missing the column gets it, whether or not the
registry happens to be populated yet.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-16T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

_DEFAULT_CLIENT = "ORG1"


def upgrade() -> None:
    conn = op.get_bind()
    tables = [
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE 'biz\\_%' ESCAPE '\\'"
            )
        ).fetchall()
    ]
    for table in tables:
        has_col = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t AND column_name = 'client_code'"
            ),
            {"t": table},
        ).fetchone()
        if has_col:
            continue
        conn.execute(
            sa.text(
                f'ALTER TABLE "{table}" ADD COLUMN client_code varchar(10) '
                f"NOT NULL DEFAULT '{_DEFAULT_CLIENT}'"
            )
        )
        conn.execute(
            sa.text(
                f'ALTER TABLE "{table}" ADD CONSTRAINT fk_{table}_client_code '
                f"FOREIGN KEY (client_code) REFERENCES clients(code)"
            )
        )
        conn.execute(sa.text(f'CREATE INDEX IF NOT EXISTS ix_{table}_client_code ON "{table}" (client_code)'))


def downgrade() -> None:
    # Additive-only repair migration; not auto-reversed.
    pass
