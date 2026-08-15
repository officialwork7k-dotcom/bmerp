"""Synchronous, idempotent periodic-run pattern for operations that would
elsewhere be a scheduled/background job — asset depreciation, recurring
billing, period-end accruals. Phase 1 explicitly excludes any new ARQ
dependency (a previously-diagnosed ARQ hang problem in this environment —
the same reason CSV import/export runs synchronously, see csv_io.py), so
these run directly inside the triggering HTTP request instead of being
queued.

Idempotency is what makes that safe to expose as a plain user-triggered
button: re-clicking "run depreciation for 2026-08" a second time (a retried
request, a double-click, a legitimately-repeated ops action) must never
double-process the period. `periodic_runs` — gated by a partial unique
index on (client_code, run_type, period_key) WHERE status='completed' — is
the log that enforces that; a failed attempt doesn't block a retry, only a
completed one does.

`register_run` lets Part 2 plug in real business logic (depreciation,
billing) without this module knowing anything about asset or CRM domain
concepts — the engine only owns the log-gating, not what a run actually
does.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.infrastructure.models import PeriodicRun

RunFunc = Callable[..., Awaitable[dict[str, Any]]]


class PeriodicRunError(Exception):
    pass


_REGISTRY: dict[str, RunFunc] = {}


def register_run(run_type: str) -> Callable[[RunFunc], RunFunc]:
    """Decorator: `@register_run("asset_depreciation")` on an async
    function `(session, *, client_code, period_key, actor_id, run_id,
    **kwargs) -> dict` — the dict becomes the run's `result_summary`.
    `run_id` is this PeriodicRun row's own id, handed to the function so a
    batch operation with no single triggering document (e.g. a
    depreciation run's journal entry, covering every asset at once) has
    something legitimate to anchor a journal_entries.document_id to — see
    infrastructure/depreciation.py."""

    def decorator(fn: RunFunc) -> RunFunc:
        _REGISTRY[run_type] = fn
        return fn

    return decorator


async def execute(
    session: AsyncSession, run_type: str, period_key: str, *, client_code: str | None, actor_id: uuid.UUID | None, **kwargs: Any
) -> PeriodicRun:
    existing = (
        await session.execute(
            select(PeriodicRun).where(
                PeriodicRun.client_code == client_code,
                PeriodicRun.run_type == run_type,
                PeriodicRun.period_key == period_key,
                PeriodicRun.status == "completed",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    fn = _REGISTRY.get(run_type)
    if fn is None:
        raise PeriodicRunError(f"no periodic run registered for type '{run_type}'")

    run = PeriodicRun(client_code=client_code, run_type=run_type, period_key=period_key, status="running", triggered_by=actor_id)
    session.add(run)
    await session.flush()

    try:
        result = await fn(session, client_code=client_code, period_key=period_key, actor_id=actor_id, run_id=run.id, **kwargs)
    except Exception as exc:
        run.status = "failed"
        run.result_summary = {"error": str(exc)}
        run.completed_at = datetime.now(timezone.utc)
        raise
    run.status = "completed"
    run.result_summary = result or {}
    run.completed_at = datetime.now(timezone.utc)
    return run
