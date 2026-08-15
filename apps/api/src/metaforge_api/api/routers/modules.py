"""Builder API: CRUD over module metadata + the schema-sync trigger.

Saving a module diffs the incoming metadata against what's stored, applies
additive DDL automatically, and returns any destructive-change warnings
instead of silently dropping them — the builder UI (Phase 4) surfaces those
warnings and requires the admin to author a manual migration for them.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from metaforge_api.api.deps import AdminUser, CurrentUserDep, DbSession
from metaforge_api.domain.schema_diff import plan_schema_diff
from metaforge_api.domain.serialization import module_from_dict, module_to_dict
from metaforge_api.infrastructure import cache, schema_sync
from metaforge_api.infrastructure.models import Module
from metaforge_api.infrastructure.module_registry import invalidate_cache

router = APIRouter(prefix="/api/modules", tags=["modules"])


class ModuleSaveIn(BaseModel):
    name: str
    label: str
    fields: list[dict]
    relationships: list[dict] = []
    workflow: dict | None = None
    posting_rules: dict | None = None
    clearing_config: dict | None = None
    stock_rules: dict | None = None
    document_flows: list[dict] | None = None
    detail_actions: dict | None = None
    create_guards: list[dict] | None = None
    hidden: bool = False


@router.get("")
async def list_modules(session: DbSession, user: CurrentUserDep):
    result = await session.execute(select(Module))
    return [{**row.metadata_json, "name": row.name, "version": row.version} for row in result.scalars()]


@router.get("/{name}")
async def get_module(name: str, session: DbSession, user: CurrentUserDep):
    cached = await cache.get_cached_module(name)
    if cached is not None:
        return cached

    row = (await session.execute(select(Module).where(Module.name == name))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "module not found")
    result = {**row.metadata_json, "name": row.name, "version": row.version}
    await cache.set_cached_module(name, result)
    return result


@router.put("/{name}")
async def save_module(name: str, body: ModuleSaveIn, session: DbSession, user: AdminUser):
    if body.name != name:
        raise HTTPException(400, "path name and body name must match")

    existing_row = (await session.execute(select(Module).where(Module.name == name))).scalar_one_or_none()
    old_module = (
        module_from_dict({**existing_row.metadata_json, "name": existing_row.name, "version": existing_row.version})
        if existing_row
        else None
    )
    new_version = (old_module.version if old_module else 0) + 1
    new_module = module_from_dict({**body.model_dump(), "version": new_version})

    plan = plan_schema_diff(old_module, new_module)

    if existing_row is None:
        session.add(Module(name=name, metadata_json=module_to_dict(new_module), version=new_version))
    else:
        existing_row.metadata_json = module_to_dict(new_module)
        existing_row.version = new_version

    try:
        written_migration = schema_sync.write_and_apply(plan, message=f"module {name} v{new_version}")
    except Exception as exc:
        # DDL runs on its own connection/transaction outside this session, so
        # a failure here must not leave the metadata row's in-memory change
        # pending — roll it back rather than let a later, unrelated request
        # accidentally flush it.
        await session.rollback()
        raise HTTPException(409, f"schema change failed: {exc}") from exc
    await session.commit()
    invalidate_cache(name)
    await cache.invalidate_cached_module(name)

    return {
        "module": {**module_to_dict(new_module)},
        "migration_written": str(written_migration) if written_migration else None,
        "warnings": [w.reason for w in plan.warnings],
    }
