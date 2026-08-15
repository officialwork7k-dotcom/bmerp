"""Turns a SchemaDiffPlan into a written Alembic revision file and applies it.

Per the plan: schema changes are additive-only (CREATE TABLE, ADD COLUMN,
ADD parent FK + index). Destructive changes are never auto-applied — they
surface as `DestructiveChangeWarning`s the caller (the /api/modules router)
must show the admin instead of calling this module.

Every change goes through a real Alembic revision file on disk, per "never
hand-edit a database schema outside a migration" — this module writes the
file and then runs `alembic upgrade head`, it never issues raw DDL directly.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from textwrap import indent

from alembic import command
from alembic.config import Config

from metaforge_api.domain.metadata import FieldDataType, FieldMetadata
from metaforge_api.domain.schema_diff import (
    AddColumnOp,
    AddDefaultFlagIndexOp,
    AddParentForeignKeyOp,
    CreateTableOp,
    RelaxNotNullOp,
    SchemaDiffPlan,
    table_name,
)

_API_DIR = Path(__file__).resolve().parents[3]
_MIGRATIONS_DIR = _API_DIR / "migrations"
_ALEMBIC_INI = _API_DIR / "alembic.ini"

_NUMERIC_TYPES = {FieldDataType.DECIMAL, FieldDataType.MONEY, FieldDataType.PERCENT}
_UUID_FK_TYPES = {FieldDataType.LOOKUP, FieldDataType.FILE, FieldDataType.IMAGE}
_TEXT_TYPES = {FieldDataType.LONG_TEXT, FieldDataType.RICH_TEXT}
_SIMPLE_SA_TYPE = {
    FieldDataType.TEXT: "sa.String(length={len})",
    FieldDataType.EMAIL: "sa.String(length={len})",
    FieldDataType.PHONE: "sa.String(length={len})",
    FieldDataType.URL: "sa.String(length={len})",
    FieldDataType.INTEGER: "sa.Integer()",
    # Stores the *formatted* value ("PO-0001"), not a raw counter — the
    # counter itself lives in number_series.next_value (an actual integer).
    # This column just holds whatever _allocate_number_series() renders,
    # prefix and zero-padding included, so it has to be a string column.
    FieldDataType.AUTO_NUMBER: "sa.String(length={len})",
    FieldDataType.DATE: "sa.Date()",
    FieldDataType.TIME: "sa.Time()",
    FieldDataType.BOOLEAN: "sa.Boolean()",
    FieldDataType.ENUM: "sa.String(length={len})",
}


def _sa_type_repr(field: FieldMetadata) -> str:
    if field.data_type in _NUMERIC_TYPES:
        return f"sa.Numeric({field.precision or 18}, {field.scale or 4})"
    if field.data_type == FieldDataType.DATETIME:
        return "sa.DateTime(timezone=True)"
    if field.data_type in _UUID_FK_TYPES:
        return "postgresql.UUID(as_uuid=True)"
    if field.data_type == FieldDataType.JSON:
        return "postgresql.JSONB()"
    if field.data_type in _TEXT_TYPES:
        return "sa.Text()"
    template = _SIMPLE_SA_TYPE.get(field.data_type)
    if template is None:
        raise ValueError(f"no Alembic column type for {field.data_type}")
    return template.format(len=field.max_length or 255)


_DEFAULT_LITERAL_TYPES = {
    FieldDataType.TEXT,
    FieldDataType.LONG_TEXT,
    FieldDataType.RICH_TEXT,
    FieldDataType.ENUM,
    FieldDataType.EMAIL,
    FieldDataType.PHONE,
    FieldDataType.URL,
    FieldDataType.AUTO_NUMBER,
}
_DEFAULT_NUMERIC_TYPES = {
    FieldDataType.INTEGER,
    FieldDataType.DECIMAL,
    FieldDataType.MONEY,
    FieldDataType.PERCENT,
}


def _server_default_sql(field: FieldMetadata) -> str | None:
    """A SQL-literal rendering of `field.default`, for use as a real column
    DEFAULT — not just app-level metadata. Without this, ADD COLUMN ...
    NOT NULL on a table that already has rows always fails: Postgres has no
    value to backfill existing rows with. Only handles the field types a
    default realistically appears on; DATE/JSON/LOOKUP defaults are rare
    enough (and harder to render safely) that they're left for a manual
    migration if ever needed."""
    if field.default is None:
        return None
    if field.data_type == FieldDataType.BOOLEAN:
        return "true" if field.default else "false"
    if field.data_type in _DEFAULT_NUMERIC_TYPES:
        return str(field.default)
    if field.data_type in _DEFAULT_LITERAL_TYPES:
        # `Column(server_default=<plain str>)` already quotes the value as a
        # SQL string literal itself (same as this file's existing
        # `server_default='1'` on the standard `version` column) — wrapping
        # it in quotes here too double-quotes it, so the stored default
        # becomes the 9-character string `'Default'`, quote marks included,
        # instead of `Default`.
        return str(field.default)
    return None


def _column_line(field: FieldMetadata) -> str:
    fk_clause = ""
    if field.data_type in _UUID_FK_TYPES and field.lookup_module:
        fk_clause = f", sa.ForeignKey('{table_name(field.lookup_module)}.id')"
    nullable = "False" if field.required else "True"
    default_sql = _server_default_sql(field)
    default_clause = f", server_default={default_sql!r}" if default_sql is not None else ""
    return f"sa.Column('{field.name}', {_sa_type_repr(field)}{fk_clause}, nullable={nullable}{default_clause}),"


_STANDARD_COLUMNS = """\
sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
sa.Column('version', sa.Integer(), server_default='1', nullable=False),
sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),\
"""


def _render_create_table(op: CreateTableOp) -> str:
    field_lines = "\n".join(_column_line(f) for f in op.fields)
    body = _STANDARD_COLUMNS + ("\n" + field_lines if field_lines else "")
    table = table_name(op.module_name)
    create = f"op.create_table(\n    '{table}',\n" + indent(body, "    ") + "\n)"
    index = f"op.create_index('ix_{table}_client_code', '{table}', ['client_code'])"
    return f"{create}\n{index}"


def _render_add_column(op: AddColumnOp) -> str:
    return f"op.add_column('{table_name(op.module_name)}', {_column_line(op.field)[:-1]})"


def _render_add_parent_fk(op: AddParentForeignKeyOp) -> str:
    child = table_name(op.child_module_name)
    parent = table_name(op.parent_module_name)
    ondelete = "CASCADE" if op.cascade_delete else "RESTRICT"
    lines = [
        f"op.add_column('{child}', sa.Column('{op.fk_column_name}', postgresql.UUID(as_uuid=True), nullable=True))",
        f"op.create_foreign_key('fk_{child}_{op.fk_column_name}', '{child}', '{parent}', "
        f"['{op.fk_column_name}'], ['id'], ondelete='{ondelete}')",
        f"op.create_index('ix_{child}_{op.fk_column_name}', '{child}', ['{op.fk_column_name}'])",
    ]
    return "\n".join(lines)


def _render_add_default_flag_index(op: AddDefaultFlagIndexOp) -> str:
    table = table_name(op.module_name)
    index_name = f"uq_{table}_{op.field_name}_default"
    # A partial unique index over the constant expression `true`, filtered
    # to only rows where the flag is set: at most one row can ever satisfy
    # the WHERE clause and be indexed, so Postgres itself rejects a second
    # `true` — race-proof, no application-level polling required. Not
    # expressible through op.create_index()'s column-list API (the indexed
    # expression is a literal, not a column), so this is raw SQL.
    # `!r` renders a properly quoted/escaped Python string literal for the
    # generated migration file — hand-embedding quote characters via an
    # f-string previously produced invalid Python (unescaped `"` inside a
    # `"..."` string), which crashed the *next* module save, not this one,
    # since it only surfaces when Alembic tries to load every revision file.
    sql = f'CREATE UNIQUE INDEX {index_name} ON {table} ((true)) WHERE "{op.field_name}"'
    return f"op.execute({sql!r})"


def _render_relax_not_null(op: RelaxNotNullOp) -> str:
    return f"op.alter_column('{table_name(op.module_name)}', '{op.field_name}', nullable=True)"


_RENDERERS = {
    CreateTableOp: _render_create_table,
    AddColumnOp: _render_add_column,
    AddParentForeignKeyOp: _render_add_parent_fk,
    AddDefaultFlagIndexOp: _render_add_default_flag_index,
    RelaxNotNullOp: _render_relax_not_null,
}


def render_migration(plan: SchemaDiffPlan, *, revision: str, down_revision: str | None, message: str) -> str:
    op_lines = "\n".join(_RENDERERS[type(op)](op) for op in plan.operations)
    upgrade_body = op_lines or "pass"
    return f'''"""{message}

Revision ID: {revision}
Revises: {down_revision or ""}
Create Date: {datetime.now(timezone.utc).isoformat()}
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "{revision}"
down_revision = {down_revision!r}
branch_labels = None
depends_on = None


def upgrade() -> None:
{indent(upgrade_body, "    ")}


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
'''


def _new_revision_id() -> str:
    return uuid.uuid4().hex[:12]


def _config() -> Config:
    config = Config(str(_ALEMBIC_INI))
    # alembic.ini's script_location is relative and gets resolved against
    # the process's cwd, which varies by launcher (uvicorn from repo root,
    # `alembic` CLI from apps/api, etc.) — pin it absolutely so schema sync
    # works regardless of where the server process was started.
    config.set_main_option("script_location", str(_MIGRATIONS_DIR))
    return config


def _current_head(config: Config) -> str | None:
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    return heads[0] if heads else None


def write_and_apply(plan: SchemaDiffPlan, *, message: str) -> Path | None:
    """Writes a migration file for `plan` (if non-empty) and applies it.

    Returns the path written, or None if the plan had no operations
    (e.g. it consisted purely of DestructiveChangeWarnings the caller
    already decided not to act on).
    """
    if not plan.operations:
        return None

    config = _config()
    down_revision = _current_head(config)
    revision = _new_revision_id()
    slug = re.sub(r"[^a-z0-9]+", "_", message.lower()).strip("_")[:40]
    filename = f"{revision}_{slug or 'schema_change'}.py"
    path = _MIGRATIONS_DIR / "versions" / filename
    path.write_text(render_migration(plan, revision=revision, down_revision=down_revision, message=message))

    try:
        command.upgrade(config, "head")
    except Exception:
        # The file must exist on disk for alembic to apply it, but if the
        # apply itself fails we must not leave it behind: a retry would
        # otherwise chain a new revision onto this unapplied one and re-run
        # DDL (e.g. CREATE TABLE) that already partially executed.
        path.unlink(missing_ok=True)
        raise
    return path
