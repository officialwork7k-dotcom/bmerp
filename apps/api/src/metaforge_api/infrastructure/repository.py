"""Transactional CRUD for dynamic module tables, including atomic
parent+embedded-children writes and aggregate recompute.

This is the fix for the audit finding that `data-form.tsx` saved a parent
and its embedded child rows as a sequence of independent REST calls with no
rollback: everything here runs inside one AsyncSession/transaction per
request.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field as dc_field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import delete, insert, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.formulas import evaluate_formula
from metaforge_api.domain.metadata import AggregateOp, FieldDataType, ModuleMetadata
from metaforge_api.domain.number_series import current_period_key
from metaforge_api.domain.schema_diff import table_name
from metaforge_api.infrastructure import approval_rules, fiscal, posting, stock
from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import AuditLog


# Server-managed on every table (see dynamic_tables.build_table); a client
# echoing a GET response back on save must never be able to set these.
_SYSTEM_COLUMNS = ("id", "created_at", "updated_at", "deleted_at", "created_by", "version", "client_code")

# Field types a free-text `?search=` term can reasonably ILIKE against —
# numeric/date/boolean/lookup columns don't have a meaningful substring
# match, so they're left to real column-equality filters instead.
_SEARCHABLE_TYPES = {
    FieldDataType.TEXT,
    FieldDataType.LONG_TEXT,
    FieldDataType.RICH_TEXT,
    FieldDataType.EMAIL,
    FieldDataType.PHONE,
    FieldDataType.URL,
    FieldDataType.AUTO_NUMBER,
}


class CreateGuardBlocked(Exception):
    """Raised when a ModuleMetadata.create_guards rule finds its flag set on
    the related record — see that field's doc comment in domain/metadata.py.
    Carries the guard's own message so the API layer doesn't have to know
    which guard fired."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class LookupScopeError(Exception):
    """Raised when a LOOKUP field's value points at a record belonging to a
    *different* client_code than the one making the write. See
    Repository._validate_lookup_scope for why this has to be checked
    explicitly rather than assumed: the UI's own lookup search only ever
    offers same-org candidates, but nothing about a raw UUID in a direct
    API payload proves it came from that search."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ConcurrencyConflict(Exception):
    """Raised when an update/transition's `WHERE version = :expected` matches
    zero rows — someone else saved this record first. Carries just enough to
    let the API layer re-fetch and return the current state; the repository
    itself doesn't know about HTTP status codes."""

    def __init__(self, module_name: str, record_id: uuid.UUID):
        self.module_name = module_name
        self.record_id = record_id
        super().__init__(f"version conflict on {module_name}/{record_id}")


def _jsonable(row: dict[str, Any]) -> dict[str, Any]:
    """UUID/Decimal/date/datetime values can't go straight into a JSONB
    column via asyncpg's json.dumps — this is only for audit_log.changes,
    never for the actual data write path (coerce_row goes the other way)."""
    import datetime as _dt
    import decimal as _decimal

    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif isinstance(v, _decimal.Decimal):
            out[k] = float(v)
        elif isinstance(v, (_dt.date, _dt.datetime, _dt.time)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def apply_formulas(module: ModuleMetadata, row: dict[str, Any]) -> dict[str, Any]:
    """Computes every formula field (e.g. line_total = qty * unit_price)
    server-side, authoritatively, regardless of what a client sent.

    This must not be a client-side-only nicety: an aggregate like a PO
    subtotal sums this column directly in SQL, so if a formula field is
    never actually written to the row, the aggregate silently stays zero.
    Assumes `row` holds the full record (every caller here does), since a
    formula referencing a field missing from a partial patch would compute
    against a false zero.

    Evaluates against `out`, not the original `row` — a formula field can
    depend on another formula field (e.g. tax_amount = line_total *
    tax_rate / 100, where line_total is itself qty * unit_price), and
    fields are declared in dependency order, so each formula sees every
    formula computed before it in this same pass rather than a stale/absent
    value from the raw input.
    """
    out = dict(row)
    for f in module.fields:
        if f.formula:
            out[f.name] = evaluate_formula(f.formula, out)
    return out

_DATE_PARSERS = {
    FieldDataType.DATE: date.fromisoformat,
    FieldDataType.TIME: time.fromisoformat,
    # asyncpg needs a real datetime object per column, not the ISO string
    # JSON delivers it as — 'Z' isn't accepted by fromisoformat pre-3.11
    # semantics some drivers rely on, so normalize it to +00:00 first.
    FieldDataType.DATETIME: lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")),
}


def apply_defaults(module: ModuleMetadata, row: dict[str, Any]) -> dict[str, Any]:
    """Fills in `field.default` for any field the caller's payload omits
    entirely. `field.default` is only ever rendered into a Postgres
    server_default when a column is first created (schema_sync.py) — later
    edits to a field's default value are never retro-applied to the column,
    and callers that don't go through DataForm's client-side seeding (a
    document-flow copy, a raw API create, a CSV import row) never send the
    field at all. Applying the metadata default here, in Python, is correct
    regardless of DDL history and doesn't require chasing whether a given
    column happens to have a matching server_default."""
    out = dict(row)
    for field in module.fields:
        if field.default is not None and field.name not in out:
            out[field.name] = field.default
    return out


def coerce_row(module: ModuleMetadata, row: dict[str, Any]) -> dict[str, Any]:
    """Converts JSON-native values (ISO date/datetime/time strings) into the
    Python types asyncpg requires for those column types. JSON has no date
    type, so every date/datetime/time field arrives as a string from the
    frontend — asyncpg (unlike some sync drivers) does not coerce these
    itself and raises a DataError on bind."""
    out = dict(row)
    for name, value in row.items():
        if value is None or not isinstance(value, str):
            continue
        field = module.field(name)
        if field is None:
            continue
        parser = _DATE_PARSERS.get(field.data_type)
        if parser is not None:
            out[name] = parser(value)
    return out


_FILTER_BOOL_TRUE = {"true", "1", "yes"}
_FILTER_NUMERIC_TYPES = {FieldDataType.INTEGER, FieldDataType.DECIMAL, FieldDataType.MONEY, FieldDataType.PERCENT, FieldDataType.AUTO_NUMBER}


def _coerce_filter_value(module: ModuleMetadata, name: str, value: Any) -> Any:
    """List-endpoint query-string filters (`?is_default=true`) arrive as
    plain strings no matter the column type — asyncpg has no implicit
    string->boolean/numeric cast the way some sync drivers do, so
    `boolean_col = 'true'` fails outright rather than just never matching.
    Mirrors coerce_row's date handling, for the read/filter side."""
    if not isinstance(value, str):
        return value
    field = module.field(name)
    if field is None:
        return value
    if field.data_type == FieldDataType.BOOLEAN:
        return value.lower() in _FILTER_BOOL_TRUE
    if field.data_type in _FILTER_NUMERIC_TYPES:
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return value
    parser = _DATE_PARSERS.get(field.data_type)
    return parser(value) if parser else value


class ModuleRegistry(Protocol):
    def get(self, name: str) -> ModuleMetadata: ...
    def all(self) -> dict[str, ModuleMetadata]: ...


@dataclass
class ChildDiff:
    """Mirrors the frontend EmbeddedGrid.getChanges() shape: rows to
    create, update, or remove for one embedded relationship."""

    create: list[dict[str, Any]] = dc_field(default_factory=list)
    update: list[dict[str, Any]] = dc_field(default_factory=list)
    remove: list[uuid.UUID] = dc_field(default_factory=list)


_AGGREGATE_SQL_OP = {
    AggregateOp.SUM: "COALESCE(SUM({col}), 0)",
    AggregateOp.COUNT: "COALESCE(COUNT(*), 0)",
    AggregateOp.MIN: "MIN({col})",
    AggregateOp.MAX: "MAX({col})",
    AggregateOp.AVG: "COALESCE(AVG({col}), 0)",
}


def build_aggregate_update_sql(
    parent_module: str,
    parent_field: str,
    child_module: str,
    fk_column: str,
    source_field: str,
    op: AggregateOp,
    *,
    filter_field: str | None = None,
) -> str:
    """Pure SQL-text builder (no execution) so it's unit-testable without a DB.

    `filter_field` (if given) adds `AND {filter_field} = :filter_value` — a
    rollup over a filtered subset of child rows (e.g. only unpaid lines),
    not just every child. The bound-parameter name is fixed so the caller
    knows what to pass alongside `parent_id`.
    """
    parent_table = table_name(parent_module)
    child_table = table_name(child_module)
    expr = _AGGREGATE_SQL_OP[op].format(col=source_field)
    filter_clause = f" AND {filter_field} = :filter_value" if filter_field else ""
    return (
        f"UPDATE {parent_table} SET {parent_field} = ("
        f"SELECT {expr} FROM {child_table} "
        f"WHERE {fk_column} = {parent_table}.id AND deleted_at IS NULL{filter_clause}"
        f") WHERE id = :parent_id"
    )


class DataRepository:
    def __init__(self, session: AsyncSession, registry: ModuleRegistry, *, client_code: str | None = None):
        self.session = session
        self.registry = registry
        # The signed-in user's active tenant (see api/deps.py) — every read
        # filters to it, every write stamps it. `None` only for the rare
        # framework-internal caller that predates client tenancy (e.g. a
        # script) and deliberately wants to bypass scoping.
        self.client_code = client_code

    def _scope(self, table, query):
        """Applies the client_code filter to a SELECT — a no-op for tables
        that (unexpectedly) don't have the column, so this stays safe to
        call unconditionally from every read path."""
        if self.client_code is not None and "client_code" in table.c:
            query = query.where(table.c.client_code == self.client_code)
        return query

    def _table_for(self, module: ModuleMetadata):
        """Builds (or fetches the cached) Table for a module, decorated with
        any parent_id FK columns other modules' embedded relationships
        attach to it — see dynamic_tables.resolve_table for why a bare
        build_table() call isn't enough here."""
        return resolve_table(module, self.registry)

    async def get(self, module_name: str, record_id: uuid.UUID) -> dict[str, Any] | None:
        module = self.registry.get(module_name)
        table = self._table_for(module)
        query = select(table).where(table.c.id == record_id, table.c.deleted_at.is_(None))
        result = await self.session.execute(self._scope(table, query))
        row = result.mappings().first()
        return dict(row) if row else None

    async def list(
        self,
        module_name: str,
        *,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        module = self.registry.get(module_name)
        table = self._table_for(module)
        query = select(table).where(table.c.deleted_at.is_(None))
        query = self._scope(table, query)
        for key, val in (filters or {}).items():
            if key in table.c:
                query = query.where(table.c[key] == _coerce_filter_value(module, key, val))
        if search:
            # Every LOOKUP picker/search box in the app (the grid cell editor,
            # the header-field popover, a plain list-page filter) hits this
            # same `?search=` query param — it was accepted at the API layer
            # (excluded from being treated as a column-equality filter) but
            # never actually implemented as a filter of its own, so every
            # search box in the app has always returned the module's first
            # `limit` rows by recency regardless of what was typed. ILIKE
            # across every text-ish field is the generic, metadata-driven
            # equivalent of "search by name/code/description" without
            # hardcoding a field name per module.
            search_fields = [f for f in module.fields if f.data_type in _SEARCHABLE_TYPES and f.name in table.c]
            if search_fields:
                pattern = f"%{search}%"
                query = query.where(or_(*(table.c[f.name].ilike(pattern) for f in search_fields)))
        query = query.order_by(table.c.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [dict(row) for row in result.mappings().all()]

    async def _unset_other_defaults(
        self, module: ModuleMetadata, table, payload: dict[str, Any], *, exclude_id: uuid.UUID | None
    ) -> None:
        """The other half of FieldMetadata.is_default_flag: the partial
        unique index (see schema_sync.py) *rejects* a second true row, it
        doesn't move the flag. "Set as default" has to mean "and unset
        whichever row had it," so that happens here, in the same
        transaction, before the row carrying the new true value is
        written — otherwise the index violation fires first."""
        for f in module.fields:
            if f.is_default_flag and payload.get(f.name) is True:
                stmt = update(table).where(table.c[f.name].is_(True)).values(**{f.name: False})
                if exclude_id is not None:
                    stmt = stmt.where(table.c.id != exclude_id)
                await self.session.execute(stmt)

    async def _allocate_number_series(self, module: ModuleMetadata, payload: dict[str, Any]) -> None:
        """Fills any AUTO_NUMBER field the client didn't already supply from
        its configured number_series counter, formatted `{prefix}{value
        zero-padded to pad_width}`. Allocated with SELECT ... FOR UPDATE
        inside the caller's transaction so two concurrent creates can never
        get the same number — the row lock serializes them, the second
        waits for the first's commit/rollback rather than racing.

        reset_policy support (never/yearly/fiscal_year/monthly): each period
        gets its own counter row, keyed by `period_key` ("" / "2026" /
        "2026-08"). Which policy is active for a field is itself stored on
        those rows (admin-configured via the number-series API), so the
        *latest* existing row for (client, module, field) is read first
        purely to discover that policy before computing which period's row
        to lock/allocate from — a fresh field with no configured row at all
        defaults to "never" (a single row, period_key "").

        Scoped by client_code (an empty string bucket for the rare
        framework-internal caller with no bound client — see
        DataRepository.__init__): each tenant gets its own counter, or
        ORG1's invoice numbers and ORG2's would silently collide/interleave
        despite the tenants otherwise being fully isolated."""
        client_code = self.client_code or ""
        for f in module.fields:
            if f.data_type != FieldDataType.AUTO_NUMBER or payload.get(f.name) is not None:
                continue
            config = (
                await self.session.execute(
                    text(
                        "SELECT prefix, pad_width, reset_policy FROM number_series "
                        "WHERE client_code = :c AND module = :m AND field = :f ORDER BY id DESC LIMIT 1"
                    ),
                    {"c": client_code, "m": module.name, "f": f.name},
                )
            ).mappings().first()
            prefix = config["prefix"] if config else ""
            pad_width = config["pad_width"] if config else 5
            reset_policy = config["reset_policy"] if config else "never"
            period_key = current_period_key(reset_policy)

            row = (
                await self.session.execute(
                    text(
                        "SELECT id, prefix, pad_width, next_value FROM number_series "
                        "WHERE client_code = :c AND module = :m AND field = :f AND period_key = :p FOR UPDATE"
                    ),
                    {"c": client_code, "m": module.name, "f": f.name, "p": period_key},
                )
            ).mappings().first()
            if row is None:
                await self.session.execute(
                    text(
                        "INSERT INTO number_series (client_code, module, field, period_key, prefix, pad_width, reset_policy) "
                        "VALUES (:c, :m, :f, :p, :prefix, :pad, :policy) "
                        "ON CONFLICT (client_code, module, field, period_key) DO NOTHING"
                    ),
                    {"c": client_code, "m": module.name, "f": f.name, "p": period_key, "prefix": prefix, "pad": pad_width, "policy": reset_policy},
                )
                row = (
                    await self.session.execute(
                        text(
                            "SELECT id, prefix, pad_width, next_value FROM number_series "
                            "WHERE client_code = :c AND module = :m AND field = :f AND period_key = :p FOR UPDATE"
                        ),
                        {"c": client_code, "m": module.name, "f": f.name, "p": period_key},
                    )
                ).mappings().one()
            next_value = row["next_value"]
            await self.session.execute(
                text("UPDATE number_series SET next_value = next_value + 1 WHERE id = :id"), {"id": row["id"]}
            )
            payload[f.name] = f"{row['prefix']}{str(next_value).zfill(row['pad_width'])}"

    async def _validate_lookup_scope(self, module: ModuleMetadata, payload: dict[str, Any]) -> None:
        """Every LOOKUP field value in `payload` must reference a row that
        belongs to this org, not another tenant's — the organization
        boundary this framework runs on isn't just "queries filter by
        client_code," it's "a record can never *point at* another org's
        data in the first place." Without this, a PO's vendor_id (or any
        other LOOKUP) could reference a vendor belonging to a different
        client_code entirely: nothing about typing a raw UUID into an API
        payload proves it came from that org's own lookup search, which is
        the only place the UI ever restricts candidates to same-org rows.
        Left unchecked, that PO would then pull the *other* org's vendor
        category, AP reconciliation account, and payment terms into every
        posting this org makes against it — a tenant-isolation break, not
        just a display glitch.

        Runs once per write, covering every LOOKUP field in one pass, so
        `_apply_lookup_defaults`/`_check_create_guards` below never have to
        scope their own related-row queries: by the time they run, every
        LOOKUP value already in `payload` is guaranteed same-org."""
        if self.client_code is None:
            return
        for field in module.fields:
            if field.data_type != FieldDataType.LOOKUP or not field.lookup_module:
                continue
            value = payload.get(field.name)
            if not value:
                continue
            related_module = self.registry.get(field.lookup_module)
            related_table = self._table_for(related_module)
            if "client_code" not in related_table.c:
                continue
            row = (
                await self.session.execute(
                    select(related_table.c.id).where(
                        related_table.c.id == value, related_table.c.client_code == self.client_code
                    )
                )
            ).first()
            if row is None:
                raise LookupScopeError(
                    f"'{field.label}' references a record that doesn't belong to this organization"
                )

    async def _apply_lookup_defaults(self, module: ModuleMetadata, payload: dict[str, Any]) -> None:
        """Resolves every FieldMetadata.default_from_lookup on this module —
        see that dataclass's docstring. Runs after coerce_row/apply_defaults
        so `base_date_field` is already a real `date`, and only fills a
        field that's still empty (falsy), never overwriting a value the
        caller actually provided."""
        for f in module.fields:
            dfl = f.default_from_lookup
            if dfl is None or payload.get(f.name):
                continue
            lookup_id = payload.get(dfl.lookup_field)
            base_date = payload.get(dfl.base_date_field)
            if not lookup_id or not base_date:
                continue
            lookup_field_meta = module.field(dfl.lookup_field)
            if lookup_field_meta is None or not lookup_field_meta.lookup_module:
                continue
            related_module = self.registry.get(lookup_field_meta.lookup_module)
            related_table = self._table_for(related_module)
            related = (
                await self.session.execute(select(related_table).where(related_table.c.id == lookup_id))
            ).mappings().first()
            if related is None:
                continue
            term_value = related.get(dfl.term_field)
            days = dfl.term_days.get(term_value)
            if days is None:
                continue
            base = base_date if isinstance(base_date, date) else date.fromisoformat(str(base_date))
            payload[f.name] = base + timedelta(days=days)

    async def _check_create_guards(self, module: ModuleMetadata, payload: dict[str, Any]) -> None:
        """Server-side enforcement of ModuleMetadata.create_guards — see that
        field's doc comment. Runs after lookup defaults so a guard on a
        LOOKUP field that only got its value from a default still fires."""
        if not module.create_guards:
            return
        for guard in module.create_guards:
            lookup_id = payload.get(guard["lookup_field"])
            if not lookup_id:
                continue
            lookup_field_meta = module.field(guard["lookup_field"])
            if lookup_field_meta is None or not lookup_field_meta.lookup_module:
                continue
            related_module = self.registry.get(lookup_field_meta.lookup_module)
            related_table = self._table_for(related_module)
            related = (
                await self.session.execute(select(related_table).where(related_table.c.id == lookup_id))
            ).mappings().first()
            if related is not None and related.get(guard["flag_field"]):
                raise CreateGuardBlocked(guard["message"])

    def _check_workflow_lock(self, module: ModuleMetadata, before: dict[str, Any] | None, payload: dict[str, Any]) -> None:
        """Server-side enforcement of workflow.states[current].locked — an
        ERP invariant (a posted/approved document is immutable) has to live
        here, not just as a disabled button in the UI, or a direct API call
        bypasses it entirely.

        Also blocks the status field itself from changing via a plain
        update() at all, locked or not: `transition()` is the only path
        that runs posting_rules/stock_rules/three-way-match, so a status
        edit that sneaks through update() (e.g. the ENUM field just typed
        into like any other field, since DataForm has no reason to know a
        workflow governs it) would silently produce a document sitting in
        its trigger_status with zero of the side effects the status is
        supposed to guarantee — a posted GR with no GR/IR journal entry is
        exactly this bug, not a posting-config gap."""
        if not module.workflow or before is None:
            return
        status_field = module.workflow.get("field")
        if not status_field:
            return
        current_status = before.get(status_field)
        if status_field in payload and payload[status_field] != current_status:
            raise PermissionError(
                f"'{status_field}' can only change via a status transition, not a direct update — "
                f"use the transition action instead"
            )
        state_cfg = (module.workflow.get("states") or {}).get(current_status, {})
        if not state_cfg.get("locked"):
            return
        # A `read_only` field is by definition never user-editable — the only
        # thing that ever writes one is a system process (depreciation's
        # accumulated_depreciation, an aggregate recompute), never a form
        # submission. Locking blocks *user* edits to a posted/approved
        # document; it was never meant to also block the system's own
        # bookkeeping on that same record (a posted fixed asset must still
        # accumulate depreciation period after period), so those fields are
        # exempt from the changed-fields check below.
        system_maintained = {f.name for f in module.fields if f.read_only}
        changed_fields = {k for k, v in payload.items() if k != "version" and before.get(k) != v}
        if changed_fields - {status_field} - system_maintained:
            raise PermissionError(
                f"record is locked in status '{current_status}'; only a status transition is allowed"
            )

    async def transition(
        self,
        module_name: str,
        record_id: uuid.UUID,
        to_status: str,
        *,
        actor_id: uuid.UUID | None = None,
        note: str | None = None,
        expected_version: int | None = None,
        bypass_approval_gate: bool = False,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """The one sanctioned way to move a locked record forward: goes
        through update() (so number-series/default-flag/audit all still
        apply) but bypasses the lock check itself, since changing the
        status field *is* the allowed action.

        `bypass_approval_gate` is set only by approvals.decide() — once a
        decider has already been verified to hold the matching rule's role,
        re-checking here would just be recursive; every other caller goes
        through the gate.

        `data`, when given, writes those fields in the *same* atomic update
        as the status change — the only way to ever set a field a locked
        record's own workflow requires only at the moment of transitioning
        (e.g. fixed_assets' disposal_proceeds/disposal_date: meaningless
        before the asset is being disposed, and the record is already
        locked by the time "disposed" is reachable, so a separate update()
        call to set them first would always be rejected by the lock check).
        Values are coerced and run through apply_formulas the same way
        update()'s payload is, merged over the record's current state so a
        posting_rules formula referencing one of these fields — or any
        existing field — sees real values, not the update() bug this same
        merge-over-`before` fixed."""
        module = self.registry.get(module_name)
        if not module.workflow:
            raise ValueError(f"module '{module_name}' has no workflow configured")
        status_field = module.workflow["field"]
        record = await self.get(module_name, record_id)
        if record is None:
            raise LookupError("record not found")
        current = record.get(status_field)
        allowed = (module.workflow.get("transitions") or {}).get(current, [])
        if to_status not in allowed:
            raise PermissionError(f"cannot transition from '{current}' to '{to_status}'")
        if not bypass_approval_gate:
            rule = await approval_rules.find_matching_rule(
                self.session, client_code=self.client_code, module_name=module_name, to_status=to_status, record=record
            )
            if rule is not None:
                raise approval_rules.ApprovalRequiredError(
                    f"transitioning to '{to_status}' requires approval — file a request and have an authorized approver decide it",
                    rule.id,
                )
        await fiscal.check(self.session, module, self.client_code, record)
        # Three-way match: only worth re-checking on the way into a locked
        # (i.e. "posted"/final) state — that's the point of no return, same
        # reasoning as workflow-lock and the fiscal-period gate.
        target_state_cfg = (module.workflow.get("states") or {}).get(to_status, {})
        if target_state_cfg.get("locked"):
            from metaforge_api.infrastructure import document_flow  # deferred: document_flow imports repository.ChildDiff

            await document_flow.check_three_way_match(self.session, self.registry, module, record_id)
        table = self._table_for(module)
        extra_payload: dict[str, Any] = {}
        if data:
            merged = apply_formulas(module, {**record, **data, status_field: to_status})
            extra_payload = coerce_row(
                module,
                {k: v for k, v in merged.items() if k in table.c and k not in _SYSTEM_COLUMNS and k != status_field},
            )
        async with self.session.begin_nested() if self.session.in_transaction() else self.session.begin():
            stmt = update(table).where(table.c.id == record_id)
            stmt = self._scope(table, stmt)
            if expected_version is not None:
                stmt = stmt.where(table.c.version == expected_version)
            result = await self.session.execute(
                stmt.values(**{status_field: to_status, "version": table.c.version + 1, **extra_payload})
            )
            if expected_version is not None and result.rowcount == 0:
                raise ConcurrencyConflict(module_name, record_id)
            record = {**record, **extra_payload}
            await self._write_audit(
                module_name, record_id, "transition", actor_id,
                {status_field: {"old": current, "new": to_status}, "note": note, **({"data": _jsonable(extra_payload)} if extra_payload else {})},
            )
            # Stock movements run before posting (not after, as originally
            # written) so a COGS posting_rules line can reference the
            # moving-average cost a stock-out movement just resolved — see
            # `_stock_issue_cost_total` below. Neither module currently
            # posting_rules-and-stock_rules together (goods_receipts) reads
            # anything stock-dependent in its formulas, so this reordering
            # doesn't change their behavior at all.
            stock_movements = []
            if module.stock_rules and to_status == module.stock_rules.get("trigger_status"):
                stock_record = {**record, status_field: to_status}
                stock_movements = await stock.apply_stock_rules(
                    self.session, module, stock_record, self.registry,
                    client_code=self.client_code, actor_id=actor_id,
                )
            # Posting happens inside the same transaction as the status
            # change: an unbalanced/misconfigured posting_rules result
            # raises PostingError and rolls the whole transition back — a
            # document can never end up in its trigger_status without a
            # valid posting to show for it.
            #
            # A module's *primary* posting_rules covers its main lifecycle
            # event (e.g. an asset's acquisition); `additional_rules` is an
            # optional list of the same {trigger_status, date_field, lines}
            # shape for a *later* lifecycle event on the same record (e.g.
            # that asset's disposal) — a second posting the record will
            # reach through a further transition, not a alternate path to
            # the same one. Matched rules and document_module are resolved
            # here so posting.post_document never has to know which trigger
            # fired; every module with only a primary ruleset (everything
            # except fixed_assets today) behaves exactly as before.
            matched_rules = None
            posting_document_module = module.name
            if module.posting_rules and to_status == module.posting_rules.get("trigger_status"):
                matched_rules = module.posting_rules
            elif module.posting_rules:
                for extra in module.posting_rules.get("additional_rules") or []:
                    if to_status == extra.get("trigger_status"):
                        matched_rules = extra
                        posting_document_module = f"{module.name}:{to_status}"
                        break
            if matched_rules:
                posted_record = {**record, status_field: to_status}
                if stock_movements:
                    # The cost side of a stock-out (e.g. a Delivery shipping
                    # against Sales Order lines): each issue's own moving-
                    # average cost *at the moment of the movement* (an issue
                    # never changes the average, so this is exactly "what it
                    # cost when it left"), summed — a posting_rules line can
                    # reference this synthetic field for a COGS entry.
                    issues = [m for m in stock_movements if m.movement_type == "issue"]
                    posted_record["_stock_issue_cost_total"] = sum(
                        (abs(m.quantity) * m.resulting_avg_cost for m in issues), Decimal("0"),
                    )
                    # Same total, split by each issued item's `item_group` —
                    # lets a posting_rules line resolve COGS/Inventory per
                    # material group (raw material vs. finished good)
                    # instead of one flat account for every delivery,
                    # mirroring the same per-group split goods_receipts
                    # already gets via per_child_grouped (that one reads a
                    # stored line amount directly; this one has to come from
                    # the stock ledger's moving-average cost instead, which
                    # only exists *after* apply_stock_rules just ran above —
                    # there's no child-row field to read it from).
                    by_group: dict[str | None, Decimal] = {}
                    for item_module_name in {m.item_module for m in issues}:
                        item_module_meta = self.registry.get(item_module_name)
                        group_field = next((f.name for f in item_module_meta.fields if f.name == "item_group"), None)
                        if group_field is None:
                            continue
                        item_table = self._table_for(item_module_meta)
                        item_ids = {m.item_id for m in issues if m.item_module == item_module_name}
                        rows = (
                            await self.session.execute(
                                select(item_table.c.id, item_table.c[group_field]).where(item_table.c.id.in_(item_ids))
                            )
                        ).all()
                        group_by_item = {r.id: getattr(r, group_field) for r in rows}
                        for m in issues:
                            if m.item_module != item_module_name:
                                continue
                            group = group_by_item.get(m.item_id)
                            by_group[group] = by_group.get(group, Decimal("0")) + abs(m.quantity) * m.resulting_avg_cost
                    if by_group:
                        posted_record["_stock_issue_cost_by_group"] = by_group
                await posting.post_document(
                    self.session, module, posted_record, self.registry,
                    client_code=self.client_code, actor_id=actor_id,
                    rules=matched_rules, document_module=posting_document_module,
                )
        return await self.get(module_name, record_id)

    async def _write_audit(
        self, module_name: str, record_id: uuid.UUID, action: str, actor_id: uuid.UUID | None, changes: dict[str, Any] | None
    ) -> None:
        self.session.add(AuditLog(module=module_name, record_id=record_id, action=action, actor_id=actor_id, changes=changes))

    async def create(
        self,
        module_name: str,
        data: dict[str, Any],
        children: dict[str, ChildDiff] | None = None,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        module = self.registry.get(module_name)
        table = self._table_for(module)
        data = apply_formulas(module, data)
        payload = coerce_row(module, {k: v for k, v in data.items() if k in table.c and k not in _SYSTEM_COLUMNS})
        payload = apply_defaults(module, payload)
        await self._validate_lookup_scope(module, payload)
        await self._apply_lookup_defaults(module, payload)
        await self._check_create_guards(module, payload)
        if actor_id is not None:
            payload["created_by"] = actor_id
        if self.client_code is not None and "client_code" in table.c:
            payload["client_code"] = self.client_code
        await fiscal.check(self.session, module, self.client_code, payload)

        async with self.session.begin_nested() if self.session.in_transaction() else self.session.begin():
            await self._allocate_number_series(module, payload)
            await self._unset_other_defaults(module, table, payload, exclude_id=None)
            result = await self.session.execute(insert(table).values(**payload).returning(table))
            parent_row = dict(result.mappings().one())
            await self._apply_children(module, parent_row["id"], children or {})
            await self._write_audit(module_name, parent_row["id"], "create", actor_id, {"new": _jsonable(payload)})

        result_row = await self.get(module_name, parent_row["id"])  # includes recomputed aggregates
        await self._dispatch_webhooks(module_name, "create", parent_row["id"], result_row)
        return result_row

    async def update(
        self,
        module_name: str,
        record_id: uuid.UUID,
        data: dict[str, Any],
        children: dict[str, ChildDiff] | None = None,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        module = self.registry.get(module_name)
        table = self._table_for(module)
        # Captured from the caller's own payload, before it gets merged with
        # `before` below — an old caller (or one that never sends version at
        # all) must still skip the concurrency check rather than accidentally
        # pick up `before`'s version and start being enforced against a check
        # it never opted into.
        expected_version = data.get("version")

        before = await self.get(module_name, record_id)
        if before is None:
            raise LookupError(f"record not found: {record_id}")
        # Formulas must be evaluated against the record's full state, not
        # just this call's (possibly partial) payload: apply_formulas treats
        # any field the formula references but the payload doesn't include
        # as 0, not "unchanged" — depreciation.py's own update only ever
        # sends {"accumulated_depreciation": x}, so evaluating
        # net_book_value = acquisition_cost - accumulated_depreciation
        # against that raw payload read acquisition_cost as 0 and wrote a
        # corrupted negative net_book_value on every depreciation run.
        # Merging over `before` first guarantees every formula's inputs are
        # real values, for every partial-update caller, not just this one.
        data = apply_formulas(module, {**before, **data})
        # The frontend seeds its editable `values` from the GET response
        # (`values = {...record}`), so every save round-trips the audit
        # columns straight back — `updated_at` in particular arrives as a
        # plain ISO string, which asyncpg's TIMESTAMPTZ binder rejects
        # (unlike psycopg, it doesn't parse date strings), turning every
        # save into an intermittent 500. These columns are server-managed
        # and must never be settable from client data.
        payload = coerce_row(
            module,
            {k: v for k, v in data.items() if k in table.c and k not in _SYSTEM_COLUMNS},
        )
        payload["version"] = table.c.version + 1
        self._check_workflow_lock(module, before, payload)
        # Only the LOOKUP fields this call actually *changes* — payload now
        # holds every field (merged over `before` above for the formula
        # fix), and a field that's unchanged since its last write was
        # already validated then; re-checking it here on every single
        # update would be a wasted query per LOOKUP field per save.
        changed_lookups = {
            f.name: payload[f.name]
            for f in module.fields
            if f.data_type == FieldDataType.LOOKUP and f.lookup_module and payload.get(f.name) != before.get(f.name)
        }
        if changed_lookups:
            await self._validate_lookup_scope(module, changed_lookups)
        # Gate on the record's *effective* period-gate value, whether or not
        # this request actually touches that field — an ERP invariant, same
        # as workflow-lock: nothing on a closed-period document is editable,
        # not just the date field itself.
        await fiscal.check(self.session, module, self.client_code, {**before, **payload})

        async with self.session.begin_nested() if self.session.in_transaction() else self.session.begin():
            await self._unset_other_defaults(module, table, payload, exclude_id=record_id)
            if payload:
                stmt = update(table).where(table.c.id == record_id)
                stmt = self._scope(table, stmt)
                if expected_version is not None:
                    stmt = stmt.where(table.c.version == expected_version)
                result = await self.session.execute(stmt.values(**payload))
                # Two clerks read the same record, both edit, first save
                # wins — the second's WHERE...AND version=:expected matches
                # zero rows instead of silently overwriting the first save.
                # The row is confirmed to exist (checked above), so a miss
                # here can only mean the version moved since this caller's
                # `before` read.
                if expected_version is not None and result.rowcount == 0:
                    raise ConcurrencyConflict(module_name, record_id)
            await self._apply_children(module, record_id, children or {})
            # Field-level before/after, not the whole row — only what
            # actually changed, which is what a history panel actually
            # needs to render ("qty: 5 -> 10"), not a full record dump.
            # Both sides go through _jsonable first: `before` comes straight
            # from asyncpg (real UUID/Decimal/datetime objects) while the
            # new values are already-jsonified strings/numbers — comparing
            # across those types directly would call every field "changed"
            # even when nothing actually did.
            before_json = _jsonable(before or {})
            diff = {
                k: {"old": before_json.get(k), "new": v}
                for k, v in _jsonable(payload).items()
                if before_json.get(k) != v and k != "version"
            }
            if diff:
                await self._write_audit(module_name, record_id, "update", actor_id, diff)

        result_row = await self.get(module_name, record_id)
        await self._dispatch_webhooks(module_name, "update", record_id, result_row)
        return result_row

    def _check_not_locked_for_delete(self, module: ModuleMetadata, existing: dict[str, Any]) -> None:
        """A posted/approved document (e.g. a posted vendor invoice, one that
        may already carry a GL posting or have payments applied against it)
        must never be deletable outright — same "locked" invariant as
        _check_workflow_lock enforces for edits, just for the delete path,
        which update()'s check doesn't cover since delete has no payload to
        diff. The only sanctioned way off a locked record is a status
        transition (e.g. reversal), never a hard delete."""
        if not module.workflow:
            return
        status_field = module.workflow.get("field")
        if not status_field:
            return
        current_status = existing.get(status_field)
        state_cfg = (module.workflow.get("states") or {}).get(current_status, {})
        if state_cfg.get("locked"):
            raise PermissionError(f"record is locked in status '{current_status}'; cannot be deleted")

    async def delete(self, module_name: str, record_id: uuid.UUID, *, actor_id: uuid.UUID | None = None) -> None:
        module = self.registry.get(module_name)
        table = self._table_for(module)
        existing = await self.get(module_name, record_id)
        if existing is not None:
            self._check_not_locked_for_delete(module, existing)
            await fiscal.check(self.session, module, self.client_code, existing)
        stmt = self._scope(table, update(table).where(table.c.id == record_id))
        await self.session.execute(stmt.values(deleted_at=text("now()")))
        await self._write_audit(module_name, record_id, "delete", actor_id, None)
        await self._dispatch_webhooks(module_name, "delete", record_id, None)

    async def _dispatch_webhooks(self, module_name: str, event: str, record_id: uuid.UUID, payload: dict[str, Any] | None) -> None:
        """Best-effort: queries active webhooks for this module+event and
        hands delivery to the ARQ worker (HMAC signing, retries-never-block
        this request). A Valkey/ARQ hiccup here must never fail the write
        that triggered it — fails soft, same policy as the cache module."""
        try:
            from metaforge_api.infrastructure import jobs
            from metaforge_api.infrastructure.models import Webhook

            rows = (
                await self.session.execute(
                    select(Webhook).where(
                        Webhook.module == module_name,
                        Webhook.is_active.is_(True),
                        or_(Webhook.client_code == self.client_code, Webhook.client_code.is_(None)),
                    )
                )
            ).scalars().all()
            for hook in rows:
                if event in (hook.events or []):
                    await jobs.enqueue("deliver_webhook", str(hook.id), event, module_name, str(record_id), _jsonable(payload or {}))
        except Exception:  # noqa: BLE001 - webhook delivery must never break the actual write
            pass

    async def list_deleted(self, module_name: str, *, limit: int = 100) -> list[dict[str, Any]]:
        module = self.registry.get(module_name)
        table = self._table_for(module)
        query = select(table).where(table.c.deleted_at.is_not(None))
        query = self._scope(table, query).order_by(table.c.deleted_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return [dict(row) for row in result.mappings().all()]

    async def restore(self, module_name: str, record_id: uuid.UUID) -> dict[str, Any] | None:
        module = self.registry.get(module_name)
        table = self._table_for(module)
        stmt = self._scope(table, update(table).where(table.c.id == record_id, table.c.deleted_at.is_not(None)))
        result = await self.session.execute(stmt.values(deleted_at=None).returning(table))
        row = result.mappings().first()
        if row is None:
            return None
        return await self.get(module_name, record_id)

    async def _apply_children(self, parent_module: ModuleMetadata, parent_id: uuid.UUID, children: dict[str, ChildDiff]) -> None:
        embedded_by_name = {r.name: r for r in parent_module.embedded_children()}

        for rel_name, diff in children.items():
            rel = embedded_by_name.get(rel_name)
            if rel is None:
                continue
            child_module = self.registry.get(rel.related_module)
            child_table = self._table_for(child_module)
            fk_col = rel.foreign_key

            if diff.remove:
                stmt = self._scope(child_table, delete(child_table).where(child_table.c.id.in_(diff.remove)))
                await self.session.execute(stmt)

            for row in diff.create:
                row = apply_formulas(child_module, row)
                row = coerce_row(child_module, {k: v for k, v in row.items() if k in child_table.c and k not in _SYSTEM_COLUMNS})
                row = apply_defaults(child_module, row)
                row[fk_col] = parent_id
                if self.client_code is not None and "client_code" in child_table.c:
                    row["client_code"] = self.client_code
                await self.session.execute(insert(child_table).values(**row))

            update_ids = [row["id"] for row in diff.update]
            existing_by_id: dict[Any, dict[str, Any]] = {}
            if update_ids:
                existing_rows = await self.session.execute(
                    self._scope(child_table, select(child_table).where(child_table.c.id.in_(update_ids)))
                )
                existing_by_id = {r["id"]: dict(r) for r in existing_rows.mappings().all()}

            for row in diff.update:
                row_id = row["id"]
                # apply_formulas needs the full row (e.g. line_total = qty *
                # unit_price) — the payload here is only the fields the caller
                # included in this particular update, which for a partial PATCH
                # can omit fields a formula depends on. Merge onto the existing
                # DB row first so formulas recompute from complete data.
                merged = {**existing_by_id.get(row_id, {}), **row}
                merged = apply_formulas(child_module, merged)
                merged = coerce_row(child_module, {k: v for k, v in merged.items() if k in child_table.c and k not in _SYSTEM_COLUMNS})
                merged[fk_col] = parent_id
                stmt = self._scope(child_table, update(child_table).where(child_table.c.id == row_id))
                await self.session.execute(stmt.values(**merged))

            if diff.create or diff.update or diff.remove:
                await self._recompute_aggregates(parent_module, rel.related_module, fk_col, parent_id)
                await self._recompute_dependent_formulas(parent_module, parent_id)

    async def _recompute_dependent_formulas(self, module: ModuleMetadata, record_id: uuid.UUID) -> None:
        """A header formula field can reference an aggregate field on the
        same row (grand_total = total + tax_total) — but apply_formulas only
        ever runs once, against the payload at the moment of the original
        create/update call, before _recompute_aggregates has written the
        real aggregate values via raw SQL. Re-evaluates every formula field
        against the row as it stands *after* aggregates just recomputed, and
        writes back only the ones whose value actually changed. No-op if
        the module has no formula fields at all."""
        if not any(f.formula for f in module.fields):
            return
        table = self._table_for(module)
        row = (await self.session.execute(select(table).where(table.c.id == record_id))).mappings().first()
        if row is None:
            return
        recomputed = apply_formulas(module, dict(row))
        updates = {f.name: recomputed[f.name] for f in module.fields if f.formula and recomputed.get(f.name) != row.get(f.name)}
        if updates:
            await self.session.execute(update(table).where(table.c.id == record_id).values(**updates))

    async def _recompute_aggregates(self, parent_module: ModuleMetadata, child_module_name: str, fk_col: str, parent_id: uuid.UUID) -> None:
        for f in parent_module.aggregate_fields():
            agg = f.aggregate
            if agg.from_module != child_module_name:
                continue
            sql = build_aggregate_update_sql(
                parent_module.name, f.name, child_module_name, fk_col, agg.source_field, agg.op,
                filter_field=agg.filter_field,
            )
            params: dict[str, Any] = {"parent_id": parent_id}
            if agg.filter_field:
                params["filter_value"] = agg.filter_value
            await self.session.execute(text(sql), params)
