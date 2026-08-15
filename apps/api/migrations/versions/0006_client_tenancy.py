"""SAP-MANDT-style client-code tenancy: a `clients` table, a `user_clients`
assignment table (mirrors user_roles), `users.default_client_code`, and a
`client_code` column stamped onto every existing dynamic module table.

Seeds a single default client 'ORG1' and assigns every existing user to it
so this ships without breaking any pre-existing login — a fresh install (or
an admin, afterward) can add more clients and reassign users as needed.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_DEFAULT_CLIENT = "ORG1"


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("code", sa.String(length=10), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "user_clients",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="CASCADE"), primary_key=True),
    )
    op.add_column(
        "users",
        sa.Column("default_client_code", sa.String(length=10), sa.ForeignKey("clients.code", ondelete="SET NULL"), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO clients (code, name) VALUES (:code, :name)"),
        {"code": _DEFAULT_CLIENT, "name": "Default Organization"},
    )
    conn.execute(
        sa.text("INSERT INTO user_clients (user_id, client_code) SELECT id, :code FROM users"),
        {"code": _DEFAULT_CLIENT},
    )
    conn.execute(sa.text("UPDATE users SET default_client_code = :code"), {"code": _DEFAULT_CLIENT})

    # Every already-created dynamic module table needs the same column new
    # tables get automatically going forward (see dynamic_tables.build_table
    # and schema_sync's _STANDARD_COLUMNS). Discovered from the `modules`
    # registry rather than hardcoded, so this migration works regardless of
    # which modules happen to exist in a given environment.
    module_names = [row[0] for row in conn.execute(sa.text("SELECT name FROM modules")).fetchall()]
    for name in module_names:
        table = f"biz_{name}"
        conn.execute(
            sa.text(
                f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS client_code varchar(10) '
                f"NOT NULL DEFAULT '{_DEFAULT_CLIENT}'"
            )
        )
        conn.execute(
            sa.text(f'ALTER TABLE "{table}" ADD CONSTRAINT fk_{table}_client_code FOREIGN KEY (client_code) REFERENCES clients(code)')
        )
        conn.execute(sa.text(f'CREATE INDEX IF NOT EXISTS ix_{table}_client_code ON "{table}" (client_code)'))


def downgrade() -> None:
    conn = op.get_bind()
    module_names = [row[0] for row in conn.execute(sa.text("SELECT name FROM modules")).fetchall()]
    for name in module_names:
        table = f"biz_{name}"
        conn.execute(sa.text(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS fk_{table}_client_code'))
        conn.execute(sa.text(f'DROP INDEX IF EXISTS ix_{table}_client_code'))
        conn.execute(sa.text(f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS client_code'))
    op.drop_column("users", "default_client_code")
    op.drop_table("user_clients")
    op.drop_table("clients")
