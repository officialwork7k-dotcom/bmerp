"""Minimal report engine: a saved (or ad-hoc) definition — source module,
group-by fields, aggregate measures, filters — compiled into one grouped
SQL query and executed. Not a Builder module (a report isn't owned by any
one module's metadata, it's a cross-cutting artifact over one), but fully
metadata-driven like everything else: no per-report code, ever.

Deliberately small: one source module per report (no joins across
modules), five aggregate ops, five filter ops. Enough to answer "totals by
X" questions (open balance by vendor, journal totals by account, stock
movements by item) without building a BI tool.
"""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.metadata import ModuleMetadata
from metaforge_api.infrastructure.dynamic_tables import resolve_table

class ReportError(Exception):
    pass


class _Registry(Protocol):
    def get(self, name: str) -> ModuleMetadata: ...


_FILTER_OPS = {
    "eq": lambda col, val: col == val,
    "neq": lambda col, val: col != val,
    "gt": lambda col, val: col > val,
    "gte": lambda col, val: col >= val,
    "lt": lambda col, val: col < val,
    "lte": lambda col, val: col <= val,
}

_MEASURE_OPS = {
    "sum": func.sum,
    "count": func.count,
    "avg": func.avg,
    "min": func.min,
    "max": func.max,
}


def _validate_definition(table, definition: dict[str, Any]) -> None:
    for field in definition.get("group_by", []):
        if field not in table.c:
            raise ReportError(f"unknown group_by field '{field}'")
    for m in definition.get("measures", []):
        if m["op"] not in _MEASURE_OPS:
            raise ReportError(f"unknown measure op '{m['op']}'")
        if m["op"] != "count" and m["field"] not in table.c:
            raise ReportError(f"unknown measure field '{m['field']}'")
    for f in definition.get("filters", []):
        if f["op"] not in _FILTER_OPS:
            raise ReportError(f"unknown filter op '{f['op']}'")
        if f["field"] not in table.c:
            raise ReportError(f"unknown filter field '{f['field']}'")


async def run_report(
    session: AsyncSession, registry: _Registry, definition: dict[str, Any], *, client_code: str | None
) -> list[dict[str, Any]]:
    module = registry.get(definition["source_module"])
    table = resolve_table(module, registry)
    _validate_definition(table, definition)

    group_by = definition.get("group_by", [])
    measures = definition.get("measures", [])
    if not group_by and not measures:
        raise ReportError("a report needs at least one group_by field or measure")

    columns = [table.c[f] for f in group_by]
    for m in measures:
        agg_func = _MEASURE_OPS[m["op"]]
        expr = agg_func(table.c.id) if m["op"] == "count" else agg_func(table.c[m["field"]])
        columns.append(expr.label(m.get("label") or f"{m['op']}_{m.get('field', 'id')}"))

    query = select(*columns).where(table.c.deleted_at.is_(None))
    if client_code is not None and "client_code" in table.c:
        query = query.where(table.c.client_code == client_code)
    for f in definition.get("filters", []):
        query = query.where(_FILTER_OPS[f["op"]](table.c[f["field"]], f["value"]))
    if group_by:
        query = query.group_by(*[table.c[f] for f in group_by])

    result = await session.execute(query)
    return [dict(row._mapping) for row in result.all()]
