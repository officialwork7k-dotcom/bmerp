"""Document flow / copy-with-reference API — see infrastructure/document_flow.py."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from metaforge_api.api.deps import CurrentUser, CurrentUserDep, Registry, Repository, require_permission
from metaforge_api.infrastructure import document_flow

router = APIRouter(prefix="/api/document-flow", tags=["document-flow"])


@router.get("/open-lines/{module}/{record_id}")
async def get_open_lines(module: str, record_id: uuid.UUID, flow: str, repo: Repository, registry: Registry, user: CurrentUserDep):
    try:
        return await document_flow.open_lines(repo.session, registry, module, record_id, flow, client_code=repo.client_code)
    except (LookupError, document_flow.DocumentFlowError) as exc:
        raise HTTPException(404 if isinstance(exc, LookupError) else 400, str(exc)) from None


@router.get("/flows-into/{module}")
async def get_flows_into(module: str, registry: Registry, user: CurrentUserDep):
    """Which other modules have a document flow that lands on `module` —
    lets a create/edit form (e.g. Vendor Invoice) discover it can offer
    "pull lines from this GR" the moment its `gr_id` LOOKUP field is filled
    in, without the frontend needing to know the relationship up front."""
    return document_flow.flows_into(registry.all(), module)


class LineSelectionIn(BaseModel):
    source_line_id: uuid.UUID
    qty: float | None = None


class CopyIn(BaseModel):
    source_module: str
    source_id: uuid.UUID
    flow_name: str
    lines: list[LineSelectionIn] | None = None


def _require_create_on(user: CurrentUser, module: str) -> None:
    if user.is_admin:
        return
    if not user.module_permissions.get(module, {}).get("create"):
        raise HTTPException(403, f"not permitted: create on {module}")


@router.post("/preview")
async def preview_copy(body: CopyIn, repo: Repository, registry: Registry, user: CurrentUserDep):
    """Same shape as /copy but computes only — no record is created, no
    open-quantity tracking is touched. For a form pulling lines into a
    document that isn't saved yet (or an existing draft being edited): the
    real `/copy` tracking only makes sense once the target document
    actually exists, so a form uses this to fill in its own in-memory grid
    instead."""
    try:
        return await document_flow.preview_copy(repo.session, registry, body.source_module, body.source_id, body.flow_name, client_code=repo.client_code)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except document_flow.DocumentFlowError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post("/copy")
async def copy_document(body: CopyIn, repo: Repository, registry: Registry, user: CurrentUserDep):
    source_module = registry.get(body.source_module)
    flow = next((f for f in source_module.document_flows or [] if f["name"] == body.flow_name), None)
    if flow is None:
        raise HTTPException(400, f"module '{body.source_module}' has no document flow named '{body.flow_name}'")
    _require_create_on(user, flow["target_module"])

    line_selections = (
        [{"source_line_id": s.source_line_id, "qty": s.qty} for s in body.lines] if body.lines is not None else None
    )
    try:
        result = await document_flow.copy_document(
            repo.session, registry, repo, body.source_module, body.source_id, body.flow_name,
            line_selections=line_selections, actor_id=uuid.UUID(user.id),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except document_flow.DocumentFlowError as exc:
        raise HTTPException(409, str(exc)) from None
    await repo.session.commit()
    return result
