"""Open items + manual clearing API — see infrastructure/clearing.py."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUser, CurrentUserDep, DbSession, Registry
from metaforge_api.infrastructure import clearing
from metaforge_api.infrastructure.models import Clearing, ClearingItem

router = APIRouter(prefix="/api/clearing", tags=["clearing"])


class ClearingItemIn(BaseModel):
    module: str
    record_id: uuid.UUID


class ClearIn(BaseModel):
    items: list[ClearingItemIn]
    description: str = ""


def _require_update_on(user: CurrentUser, modules: set[str]) -> None:
    """Clearing mutates cross-module semantic state without going through
    DataRepository.update() on the documents themselves, so the usual
    per-route require_permission("update") dependency (keyed off a single
    path `module` param) doesn't apply here — this checks it manually
    against every module actually involved."""
    if user.is_admin:
        return
    missing = [m for m in modules if not user.module_permissions.get(m, {}).get("update")]
    if missing:
        raise HTTPException(403, f"not permitted: update on {', '.join(sorted(missing))}")


@router.get("/open-items/{module}")
async def open_items(
    module: str, session: DbSession, registry: Registry, user: CurrentUserDep,
    party_field: str | None = None, party_value: str | None = None, limit: int = 100,
):
    try:
        return await clearing.list_open_items(
            session, registry, module, client_code=user.client_code,
            party_field=party_field, party_value=party_value, limit=limit,
        )
    except clearing.ClearingError as exc:
        raise HTTPException(400, str(exc)) from None


@router.post("")
async def create_clearing(body: ClearIn, session: DbSession, registry: Registry, user: CurrentUserDep):
    _require_update_on(user, {it.module for it in body.items})
    try:
        result = await clearing.clear(
            session, registry, [it.model_dump() for it in body.items],
            client_code=user.client_code, actor_id=uuid.UUID(user.id), description=body.description,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except clearing.ClearingError as exc:
        raise HTTPException(409, str(exc)) from None
    await session.commit()
    return await _clearing_out(session, result.id)


@router.get("")
async def list_clearings(session: DbSession, user: CurrentUserDep, limit: int = 50):
    query = select(Clearing).where(Clearing.client_code == user.client_code).order_by(Clearing.cleared_at.desc()).limit(min(limit, 200))
    rows = (await session.execute(query)).scalars().all()
    return [
        {"id": str(c.id), "description": c.description, "status": c.status, "cleared_at": c.cleared_at.isoformat()}
        for c in rows
    ]


@router.get("/{clearing_id}")
async def get_clearing(clearing_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    row = (
        await session.execute(select(Clearing).where(Clearing.id == clearing_id, Clearing.client_code == user.client_code))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "clearing not found")
    return await _clearing_out(session, clearing_id)


@router.post("/{clearing_id}/reverse")
async def reverse(clearing_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    row = (
        await session.execute(select(Clearing).where(Clearing.id == clearing_id, Clearing.client_code == user.client_code))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "clearing not found")
    items = (await session.execute(select(ClearingItem).where(ClearingItem.clearing_id == clearing_id))).scalars().all()
    _require_update_on(user, {it.module for it in items})
    try:
        await clearing.reverse_clearing(session, clearing_id)
    except (LookupError, clearing.ClearingError) as exc:
        raise HTTPException(409, str(exc)) from None
    await session.commit()
    return await _clearing_out(session, clearing_id)


async def _clearing_out(session: DbSession, clearing_id: uuid.UUID) -> dict[str, Any]:
    row = (await session.execute(select(Clearing).where(Clearing.id == clearing_id))).scalar_one()
    items = (await session.execute(select(ClearingItem).where(ClearingItem.clearing_id == clearing_id))).scalars().all()
    return {
        "id": str(row.id),
        "description": row.description,
        "status": row.status,
        "cleared_at": row.cleared_at.isoformat(),
        "items": [
            {"module": it.module, "record_id": str(it.record_id), "amount": float(it.amount)} for it in items
        ],
    }
