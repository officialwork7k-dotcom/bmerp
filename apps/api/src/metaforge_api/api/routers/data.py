"""Generic CRUD for any module's dynamic table, including the nested
parent+embedded-children write that replaces the old sequential-REST-calls
save path.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

from metaforge_api.api.deps import CurrentUser, DbSession, Registry, Repository, require_permission
from metaforge_api.infrastructure import csv_io, sod
from metaforge_api.infrastructure.approval_rules import ApprovalRequiredError
from metaforge_api.infrastructure.document_flow import ThreeWayMatchError
from metaforge_api.infrastructure.fiscal import PeriodClosedError
from metaforge_api.infrastructure.posting import PostingError
from metaforge_api.infrastructure.repository import ChildDiff, ConcurrencyConflict, CreateGuardBlocked, LookupScopeError
from metaforge_api.infrastructure.stock import StockError

router = APIRouter(prefix="/api/data", tags=["data"])

_RESERVED_QUERY_PARAMS = {"limit", "offset", "search"}

CanRead = Annotated[CurrentUser, Depends(require_permission("read"))]
CanCreate = Annotated[CurrentUser, Depends(require_permission("create"))]
CanUpdate = Annotated[CurrentUser, Depends(require_permission("update"))]
CanDelete = Annotated[CurrentUser, Depends(require_permission("delete"))]


class ChildDiffIn(BaseModel):
    create: list[dict[str, Any]] = []
    update: list[dict[str, Any]] = []
    remove: list[uuid.UUID] = []


class RecordWriteIn(BaseModel):
    data: dict[str, Any]
    children: dict[str, ChildDiffIn] = {}


def _to_child_diffs(children: dict[str, ChildDiffIn]) -> dict[str, ChildDiff]:
    return {
        name: ChildDiff(create=diff.create, update=diff.update, remove=diff.remove)
        for name, diff in children.items()
    }


@router.get("/{module}")
async def list_records(module: str, request: Request, repo: Repository, user: CanRead, limit: int = 50, offset: int = 0, search: str | None = None):
    filters = {k: v for k, v in request.query_params.items() if k not in _RESERVED_QUERY_PARAMS}
    return await repo.list(module, filters=filters, search=search, limit=min(limit, 200), offset=offset)


@router.get("/{module}/deleted")
async def list_deleted_records(module: str, repo: Repository, user: CanDelete, limit: int = 100):
    """The recycle bin: soft-deleted rows for this module, newest first."""
    return await repo.list_deleted(module, limit=limit)


@router.post("/{module}/{record_id}/restore")
async def restore_record(module: str, record_id: uuid.UUID, repo: Repository, user: CanDelete):
    record = await repo.restore(module, record_id)
    if record is None:
        raise HTTPException(404, "record not found in recycle bin")
    return record


@router.get("/{module}/{record_id}/history")
async def record_history(module: str, record_id: uuid.UUID, session: DbSession, user: CanRead):
    """The audit trail for one record — old/new field values per change,
    who made it and when. The visible half of audit_log."""
    from sqlalchemy import select

    from metaforge_api.infrastructure.models import AuditLog, User

    rows = (
        await session.execute(
            select(AuditLog, User.display_name)
            .outerjoin(User, User.id == AuditLog.actor_id)
            .where(AuditLog.module == module, AuditLog.record_id == record_id)
            .order_by(AuditLog.created_at.desc())
        )
    ).all()
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "changes": log.changes,
            "actor": actor_name or "system",
            "created_at": log.created_at.isoformat(),
        }
        for log, actor_name in rows
    ]


@router.get("/{module}/{record_id}")
async def get_record(module: str, record_id: uuid.UUID, repo: Repository, user: CanRead):
    record = await repo.get(module, record_id)
    if record is None:
        raise HTTPException(404, "record not found")
    return record


async def _enforce_sod(repo: Repository, *, module: str, action: str, actor_id: uuid.UUID, record_id: uuid.UUID | None, data: dict[str, Any] | None) -> None:
    current_record = await repo.get(module, record_id) if record_id is not None else None
    violations = await sod.check(
        repo.session, module_name=module, action=action, actor_id=actor_id,
        record_id=record_id, data=data, current_record=current_record,
    )
    if violations:
        raise HTTPException(409, {"error": "sod_conflict", "violations": violations})


@router.post("/{module}")
async def create_record(module: str, body: RecordWriteIn, repo: Repository, user: CanCreate):
    actor_id = uuid.UUID(user.id)
    await _enforce_sod(repo, module=module, action="create", actor_id=actor_id, record_id=None, data=body.data)
    try:
        return await repo.create(module, body.data, _to_child_diffs(body.children), actor_id=actor_id)
    except PeriodClosedError as exc:
        raise HTTPException(409, {"error": "period_closed", "message": str(exc)}) from None
    except CreateGuardBlocked as exc:
        raise HTTPException(409, {"error": "create_blocked", "message": exc.message}) from None
    except LookupScopeError as exc:
        raise HTTPException(400, {"error": "lookup_out_of_scope", "message": exc.message}) from None


@router.patch("/{module}/{record_id}")
async def update_record(module: str, record_id: uuid.UUID, body: RecordWriteIn, repo: Repository, user: CanUpdate):
    actor_id = uuid.UUID(user.id)
    await _enforce_sod(repo, module=module, action="update", actor_id=actor_id, record_id=record_id, data=body.data)
    try:
        record = await repo.update(module, record_id, body.data, _to_child_diffs(body.children), actor_id=actor_id)
    except ConcurrencyConflict:
        current = await repo.get(module, record_id)
        raise HTTPException(409, {"error": "version_conflict", "message": "This record was changed by someone else — reload to see the latest version.", "current": current}) from None
    except LookupError:
        raise HTTPException(404, "record not found") from None
    except PeriodClosedError as exc:
        raise HTTPException(409, {"error": "period_closed", "message": str(exc)}) from None
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from None
    except LookupScopeError as exc:
        raise HTTPException(400, {"error": "lookup_out_of_scope", "message": exc.message}) from None
    if record is None:
        raise HTTPException(404, "record not found")
    return record


class TransitionIn(BaseModel):
    to: str
    note: str | None = None
    version: int | None = None
    # Fields to write in the same atomic update as the status change — the
    # only way to set a field a workflow only needs at the moment of
    # transitioning into a locked state (e.g. fixed_assets' disposal_
    # proceeds/disposal_date), since a locked record rejects a separate
    # update() call to set them first. See repository.transition()'s
    # docstring for the full reasoning.
    data: dict[str, Any] | None = None


@router.post("/{module}/{record_id}/transition")
async def transition_record(module: str, record_id: uuid.UUID, body: TransitionIn, repo: Repository, user: CanUpdate):
    actor_id = uuid.UUID(user.id)
    await _enforce_sod(repo, module=module, action=f"transition:{body.to}", actor_id=actor_id, record_id=record_id, data=body.data)
    try:
        return await repo.transition(module, record_id, body.to, actor_id=actor_id, note=body.note, expected_version=body.version, data=body.data)
    except ConcurrencyConflict:
        current = await repo.get(module, record_id)
        raise HTTPException(409, {"error": "version_conflict", "message": "This record was changed by someone else — reload to see the latest version.", "current": current}) from None
    except LookupError:
        raise HTTPException(404, "record not found") from None
    except PeriodClosedError as exc:
        raise HTTPException(409, {"error": "period_closed", "message": str(exc)}) from None
    except PostingError as exc:
        raise HTTPException(409, {"error": "posting_failed", "message": str(exc)}) from None
    except StockError as exc:
        raise HTTPException(409, {"error": "stock_failed", "message": str(exc)}) from None
    except ThreeWayMatchError as exc:
        raise HTTPException(409, {"error": "three_way_match_failed", "message": str(exc)}) from None
    except ApprovalRequiredError as exc:
        # 403, not 409: mirrors the RBAC "no update permission" case, so the
        # frontend's existing "on 403, offer to request approval" fallback
        # (WorkflowBar.svelte) handles this exactly the same way — a rule-
        # gated transition and a permission-gated one both mean "you can't
        # do this yourself, file a request instead."
        raise HTTPException(403, {"error": "approval_required", "message": str(exc), "rule_id": str(exc.rule_id)}) from None
    except (PermissionError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from None


@router.delete("/{module}/{record_id}", status_code=204)
async def delete_record(module: str, record_id: uuid.UUID, repo: Repository, user: CanDelete):
    actor_id = uuid.UUID(user.id)
    await _enforce_sod(repo, module=module, action="delete", actor_id=actor_id, record_id=record_id, data=None)
    try:
        await repo.delete(module, record_id, actor_id=actor_id)
    except PeriodClosedError as exc:
        raise HTTPException(409, {"error": "period_closed", "message": str(exc)}) from None
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post("/{module}/export")
async def export_records(module: str, repo: Repository, user: CanRead):
    """Synchronous: generates the CSV directly in this request. See
    csv_io.py's docstring for why this isn't routed through the ARQ
    worker/S3 the way it originally was."""
    content = await csv_io.export_csv(repo, module)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{module}.csv"'},
    )


@router.post("/{module}/import")
async def import_records(module: str, file: UploadFile, session: DbSession, registry: Registry, repo: Repository, user: CanCreate):
    """Synchronous row-by-row import against the same DataRepository.create()
    path a normal form submit uses. See csv_io.py's docstring."""
    content = await file.read()
    return await csv_io.import_csv(session, registry, repo, module, content, uuid.UUID(user.id))
