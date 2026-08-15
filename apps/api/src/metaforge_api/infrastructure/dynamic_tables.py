"""Builds SQLAlchemy Core Table objects at runtime from a module's metadata.

Every business table gets: id (uuid pk), created_at, updated_at, created_by,
deleted_at, version — matching the framework's audit/optimistic-concurrency
columns. Cached per (module name, module version) so a metadata edit gets a
fresh Table object without restarting the process.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from metaforge_api.domain.metadata import ModuleMetadata
from metaforge_api.domain.schema_diff import table_name
from metaforge_api.infrastructure.column_types import column_type_for_field, is_foreign_key_field

_metadata = MetaData()
_table_cache: dict[tuple[str, int], Table] = {}


def build_table(module: ModuleMetadata) -> Table:
    """Return the (cached) SQLAlchemy Table for this module's current metadata version."""
    cache_key = (module.name, module.version)
    if cache_key in _table_cache:
        return _table_cache[cache_key]

    name = table_name(module.name)
    # Re-declaring a Table with the same name replaces the prior version in
    # our own MetaData registry so stale versions don't accumulate.
    if name in _metadata.tables:
        _metadata.remove(_metadata.tables[name])

    columns: list[Column] = [
        Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")),
        Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column("created_by", UUID(as_uuid=True), nullable=True),
        Column("deleted_at", DateTime(timezone=True), nullable=True),
        Column("version", Integer, server_default="1", nullable=False),
        # SAP-MANDT-style tenant scoping (see repository.py) — every dynamic
        # module table carries this, stamped/filtered by DataRepository, never
        # settable from client data (see repository._SYSTEM_COLUMNS).
        Column("client_code", String(10), ForeignKey("clients.code"), server_default="ORG1", nullable=False),
    ]

    # Parent-child FK columns live on the *child* module's table and are
    # attached separately via add_parent_fk_column once schema_sync applies
    # the corresponding AddParentForeignKeyOp.

    for field in module.fields:
        col_kwargs = {"nullable": not field.required}
        if is_foreign_key_field(field) and field.lookup_module:
            fk_target = f"{table_name(field.lookup_module)}.id"
            columns.append(Column(field.name, column_type_for_field(field), ForeignKey(fk_target), **col_kwargs))
        else:
            columns.append(Column(field.name, column_type_for_field(field), **col_kwargs))

    table = Table(name, _metadata, *columns, extend_existing=True)
    _table_cache[cache_key] = table
    return table


def add_parent_fk_column(child_table: Table, parent_module_name: str, fk_column_name: str, cascade_delete: bool) -> Column:
    """Attach the typed parent_id FK column to an already-built child Table.

    Called by schema_sync when applying an AddParentForeignKeyOp so the
    in-memory Table object matches the DDL that was just applied.
    """
    ondelete = "CASCADE" if cascade_delete else "RESTRICT"
    # Nullable at the DB level; the repository enforces parent_id is present
    # for embedded-child writes (a NOT NULL constraint would block additive
    # rollout onto tables that already have rows).
    col = Column(
        fk_column_name,
        UUID(as_uuid=True),
        ForeignKey(f"{table_name(parent_module_name)}.id", ondelete=ondelete),
        nullable=True,
    )
    if fk_column_name not in child_table.c:
        child_table.append_column(col)
        Index(f"ix_{child_table.name}_{fk_column_name}", col)
    return child_table.c[fk_column_name]


def resolve_table(module: ModuleMetadata, registry) -> Table:
    """`build_table()` plus every parent_id FK column any OTHER module's
    embedded relationship attaches to this one — the exact augmentation
    `DataRepository._table_for()` applies, factored out here so every
    caller that reads/writes a table which might be someone else's
    embedded child (the posting/stock/document-flow engines, not just the
    repository) gets it too.

    This matters because `build_table()` alone is undecorated: a bare call
    returns a Table missing the child's own parent_id column entirely,
    since that column isn't part of the child module's own FieldMetadata —
    it only exists because *another* module embeds it. Whether a bare
    `build_table()` call "accidentally" already sees that column depends on
    whether some earlier call in the process happened to go through this
    function first for the same cached (name, version) Table object — not
    something calling code should ever rely on.

    `registry` only needs `.all() -> dict[str, ModuleMetadata]` (the same
    minimal surface `DataRepository` depends on already).
    """
    table = build_table(module)
    for other in registry.all().values():
        for rel in other.embedded_children():
            if rel.related_module == module.name:
                add_parent_fk_column(table, other.name, rel.foreign_key, rel.cascade_delete)
    return table
