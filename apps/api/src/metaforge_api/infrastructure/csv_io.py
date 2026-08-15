"""Synchronous CSV export/import, generic across every module.

Originally routed through the ARQ worker + S3 (see worker.py's now-removed
export_module_csv/import_module_csv) to keep bulk I/O off the request
thread. That path requires Valkey (ARQ's queue backend) and an S3-compatible
store to both be reachable — in an environment where either is down (as
Valkey is here), `jobs.enqueue()` doesn't fail, it hangs indefinitely
waiting to connect, which would leave Export/Import spinning forever with
no error. The record counts this framework actually deals with (a handful
to a few thousand rows per module) make synchronous CSV generation/parsing
trivially fast, so doing it directly in the request handler removes that
failure mode entirely rather than papering over it.
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any

from metaforge_api.infrastructure.module_registry import SessionModuleRegistry
from metaforge_api.infrastructure.repository import DataRepository, coerce_row


async def export_csv(repo: DataRepository, module_name: str) -> bytes:
    rows = await repo.list(module_name, filters={}, limit=10_000)
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


async def import_csv(
    session: Any, registry: SessionModuleRegistry, repo: DataRepository, module_name: str, content: bytes, actor_id: uuid.UUID
) -> dict[str, Any]:
    """Row-by-row create against the same DataRepository.create() path a
    normal form submit uses — formulas, number series, default-flag
    enforcement, and audit logging all apply exactly the same way, so an
    imported row is indistinguishable from a manually entered one. Column
    headers must match field names; unknown columns are ignored, missing
    required fields fail that row without aborting the rest of the file."""
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    module = registry.get(module_name)
    field_names = {f.name for f in module.fields}

    created = 0
    errors: list[dict[str, Any]] = []
    for i, raw_row in enumerate(reader, start=2):  # header is row 1
        row = {k: v for k, v in raw_row.items() if v not in (None, "") and k in field_names}
        try:
            await repo.create(module_name, coerce_row(module, row), actor_id=actor_id)
            await session.commit()
            created += 1
        except Exception as exc:  # noqa: BLE001 - one bad row must not sink the whole import
            await session.rollback()
            errors.append({"row": i, "error": str(exc)})

    return {"created": created, "errors": errors}
