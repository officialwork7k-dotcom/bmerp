"""Synchronous idempotent periodic-run API — see infrastructure/periodic_runs.py."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from metaforge_api.api.deps import AdminUser, DbSession
from metaforge_api.infrastructure import periodic_runs
from metaforge_api.infrastructure.models import PeriodicRun

router = APIRouter(prefix="/api/periodic-runs", tags=["periodic-runs"])


def _run_out(r: PeriodicRun) -> dict:
    return {
        "id": str(r.id),
        "run_type": r.run_type,
        "period_key": r.period_key,
        "status": r.status,
        "result_summary": r.result_summary,
        "started_at": r.started_at.isoformat(),
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


@router.get("")
async def list_runs(session: DbSession, user: AdminUser, run_type: str | None = None, limit: int = 50):
    query = select(PeriodicRun).where(PeriodicRun.client_code == user.client_code)
    if run_type:
        query = query.where(PeriodicRun.run_type == run_type)
    query = query.order_by(PeriodicRun.started_at.desc()).limit(min(limit, 200))
    rows = (await session.execute(query)).scalars().all()
    return [_run_out(r) for r in rows]


@router.post("/{run_type}/{period_key}")
async def trigger_run(run_type: str, period_key: str, session: DbSession, user: AdminUser):
    """Runs synchronously in this request — see the module docstring for
    why (no ARQ dependency in phase 1). Safe to click twice: a second call
    for an already-completed (run_type, period_key) returns the existing
    result instead of re-executing."""
    try:
        run = await periodic_runs.execute(session, run_type, period_key, client_code=user.client_code, actor_id=uuid.UUID(user.id))
    except periodic_runs.PeriodicRunError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from None
    except Exception as exc:
        # Must roll back, not commit: `execute()` only catches the run
        # function's own exception to stamp the PeriodicRun row 'failed'
        # before re-raising — it never undoes whatever that function already
        # wrote to the session (e.g. depreciation.run() calls repo.update()
        # once per qualifying asset *before* it gets to parsing period_key
        # for the posting date, so a malformed period_key like "2026-09-
        # redo" let every asset's accumulated_depreciation mutation ride
        # along into a commit here, even though the run as a whole "failed"
        # and produced no journal entry for it). A failed run must discard
        # everything it did, including its own failure log row — losing
        # that audit trail is a strictly better outcome than a periodic
        # run silently corrupting financial data it reports as failed.
        await session.rollback()
        raise HTTPException(500, f"periodic run failed: {exc}") from None
    await session.commit()
    return _run_out(run)
