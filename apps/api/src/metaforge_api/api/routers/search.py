"""Global search across every module's text-ish fields.

Not tsvector-indexed full-text search (that needs a generated column +
GIN index per dynamic table, added by schema_sync on every module save —
real future work, flagged rather than half-built here). This is the
constrained-environment version: an ILIKE OR-scan across each module's
TEXT/LONG_TEXT/EMAIL/ENUM columns, capped per module and in total. Fine at
ERP-list-page data volumes (hundreds to low thousands of rows per module on
this VM's Postgres allocation); would need real FTS before it'd hold up at
much larger scale.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import or_, select

from metaforge_api.api.deps import CurrentUserDep, DbSession, Registry
from metaforge_api.domain.metadata import FieldDataType
from metaforge_api.infrastructure.dynamic_tables import build_table

router = APIRouter(prefix="/api/search", tags=["search"])

_SEARCHABLE_TYPES = {FieldDataType.TEXT, FieldDataType.LONG_TEXT, FieldDataType.EMAIL, FieldDataType.ENUM, FieldDataType.PHONE, FieldDataType.URL}
_PER_MODULE_LIMIT = 5
_TOTAL_LIMIT = 25


@router.get("")
async def global_search(q: str, session: DbSession, registry: Registry, user: CurrentUserDep):
    q = q.strip()
    if len(q) < 2:
        return {"results": []}

    results = []
    for module in registry.all().values():
        if not user.is_admin and not user.module_permissions.get(module.name, {}).get("read"):
            continue
        text_fields = [f for f in module.fields if f.data_type in _SEARCHABLE_TYPES]
        if not text_fields:
            continue
        table = build_table(module)
        conditions = [table.c[f.name].ilike(f"%{q}%") for f in text_fields if f.name in table.c]
        if not conditions:
            continue
        conds = [table.c.deleted_at.is_(None), or_(*conditions)]
        if "client_code" in table.c:
            conds.append(table.c.client_code == user.client_code)
        query = select(table).where(*conds).limit(_PER_MODULE_LIMIT)
        rows = (await session.execute(query)).mappings().all()
        label_field = text_fields[0].name
        for row in rows:
            results.append(
                {
                    "module": module.name,
                    "module_label": module.label,
                    "id": str(row["id"]),
                    "label": str(row.get(label_field, row["id"])),
                }
            )
        if len(results) >= _TOTAL_LIMIT:
            break

    return {"results": results[:_TOTAL_LIMIT]}
