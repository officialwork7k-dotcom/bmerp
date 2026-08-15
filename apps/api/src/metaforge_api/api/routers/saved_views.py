from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select

from metaforge_api.api.deps import CurrentUserDep, DbSession
from metaforge_api.infrastructure.models import SavedView

router = APIRouter(prefix="/api/saved-views", tags=["saved-views"])


class SavedViewIn(BaseModel):
    module: str
    name: str
    config: dict = {}
    is_default: bool = False
    shared: bool = False


def _out(v: SavedView) -> dict:
    return {
        "id": str(v.id),
        "module": v.module,
        "name": v.name,
        "config": v.config,
        "is_default": v.is_default,
        "shared": v.user_id is None,
    }


@router.get("")
async def list_views(module: str, session: DbSession, user: CurrentUserDep):
    """Views visible to this user for a module: their own, plus shared
    (user_id IS NULL) ones — scoped to the caller's org. Existing rows
    with client_code IS NULL are treated as legacy/global, same as
    ApprovalRule."""
    rows = (
        await session.execute(
            select(SavedView).where(
                SavedView.module == module,
                or_(SavedView.user_id == uuid.UUID(user.id), SavedView.user_id.is_(None)),
                or_(SavedView.client_code == user.client_code, SavedView.client_code.is_(None)),
            )
        )
    ).scalars().all()
    return [_out(v) for v in rows]


@router.post("")
async def create_view(body: SavedViewIn, session: DbSession, user: CurrentUserDep):
    view = SavedView(
        module=body.module,
        user_id=None if body.shared else uuid.UUID(user.id),
        client_code=user.client_code,
        name=body.name,
        config=body.config,
        is_default=body.is_default,
    )
    session.add(view)
    await session.commit()
    return _out(view)


@router.delete("/{view_id}", status_code=204)
async def delete_view(view_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    row = (await session.execute(select(SavedView).where(SavedView.id == view_id))).scalar_one_or_none()
    if row is None:
        return
    if row.client_code is not None and row.client_code != user.client_code:
        raise HTTPException(403, "not your view")
    if row.user_id is not None and str(row.user_id) != user.id:
        raise HTTPException(403, "not your view")
    await session.delete(row)
    await session.commit()
