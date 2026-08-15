"""Open items + manual clearing: matches records across one or more
clearing-enabled modules (see ModuleMetadata.clearing_config) whose signed
amounts net to (approximately) zero — e.g. an AP invoice against the
payment(s) that settle it — and marks them cleared together.

Engine-owned tables (clearings/clearing_items), not a Builder module: "which
documents are still open" is a query derived from clearing_items, not a
column any single dynamic table owns, and "do these net to zero" is
algorithmic validation metadata can't express. Same tier as posting.py.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.metadata import ModuleMetadata
from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import Clearing, ClearingItem

_TOLERANCE = Decimal("0.01")


class ClearingError(Exception):
    pass


class _Registry(Protocol):
    def get(self, name: str) -> ModuleMetadata: ...


@dataclass
class _ResolvedItem:
    module: str
    record_id: uuid.UUID
    amount: Decimal
    party_value: Any


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _posted_only_filter(module: ModuleMetadata, table):
    """A document that never reached its posting_rules.trigger_status never
    hit the GL — including it as an "open item" would let a draft (or
    otherwise never-posted) record inflate AP/AR subledger totals past what
    the trial balance actually shows for the same account, since the two
    are computed from entirely different sources (this module's own table
    vs. journal_lines). Every module with a `clearing_config` in this app
    also has `posting_rules`, so this generically ties "counts as an open
    item" to "actually posted" without hardcoding module names — a future
    clearing-enabled module only needs the same two config blocks to get
    this for free."""
    if not module.posting_rules or not module.workflow:
        return None
    trigger_status = module.posting_rules.get("trigger_status")
    status_field = module.workflow.get("field")
    if not trigger_status or not status_field or status_field not in table.c:
        return None
    return table.c[status_field] == trigger_status


async def _resolve_item(
    session: AsyncSession, registry: _Registry, module_name: str, record_id: uuid.UUID, client_code: str | None
) -> _ResolvedItem:
    module = registry.get(module_name)
    cfg = module.clearing_config
    if not cfg:
        raise ClearingError(f"module '{module_name}' is not clearing-enabled")
    table = resolve_table(module, registry)
    query = select(table).where(table.c.id == record_id, table.c.deleted_at.is_(None))
    if client_code is not None and "client_code" in table.c:
        query = query.where(table.c.client_code == client_code)
    posted_filter = _posted_only_filter(module, table)
    if posted_filter is not None:
        query = query.where(posted_filter)
    row = (await session.execute(query)).mappings().first()
    if row is None:
        raise LookupError(f"record not found: {module_name}/{record_id}")

    already = (
        await session.execute(
            select(ClearingItem)
            .join(Clearing, Clearing.id == ClearingItem.clearing_id)
            .where(ClearingItem.module == module_name, ClearingItem.record_id == record_id, Clearing.status == "active")
        )
    ).scalar_one_or_none()
    if already is not None:
        raise ClearingError(f"{module_name}/{record_id} is already cleared")

    sign = 1 if cfg.get("sign", "positive") == "positive" else -1
    amount = _to_decimal(row.get(cfg["amount_field"])) * sign
    party_field = cfg.get("party_field")
    party_value = row.get(party_field) if party_field else None
    return _ResolvedItem(module=module_name, record_id=record_id, amount=amount, party_value=party_value)


async def list_open_items(
    session: AsyncSession, registry: _Registry, module_name: str, *,
    client_code: str | None, party_field: str | None = None, party_value: Any = None, limit: int = 100,
) -> list[dict[str, Any]]:
    module = registry.get(module_name)
    cfg = module.clearing_config
    if not cfg:
        raise ClearingError(f"module '{module_name}' is not clearing-enabled")
    table = resolve_table(module, registry)

    cleared_ids = select(ClearingItem.record_id).join(Clearing, Clearing.id == ClearingItem.clearing_id).where(
        ClearingItem.module == module_name, Clearing.status == "active"
    )
    query = select(table).where(table.c.deleted_at.is_(None), table.c.id.not_in(cleared_ids))
    if client_code is not None and "client_code" in table.c:
        query = query.where(table.c.client_code == client_code)
    if party_field and party_value is not None and party_field in table.c:
        query = query.where(table.c[party_field] == party_value)
    posted_filter = _posted_only_filter(module, table)
    if posted_filter is not None:
        query = query.where(posted_filter)
    query = query.order_by(table.c.created_at.asc()).limit(min(limit, 500))
    rows = (await session.execute(query)).mappings().all()
    return [dict(r) for r in rows]


async def clear(
    session: AsyncSession, registry: _Registry, items: list[dict[str, Any]], *,
    client_code: str | None, actor_id: uuid.UUID | None, description: str = "",
) -> Clearing:
    if len(items) < 2:
        raise ClearingError("clearing requires at least two items")

    resolved = [
        await _resolve_item(session, registry, it["module"], it["record_id"], client_code) for it in items
    ]

    party_values = {str(r.party_value) for r in resolved if r.party_value is not None}
    if len(party_values) > 1:
        raise ClearingError("selected items belong to different parties and cannot be cleared together")

    total = sum((r.amount for r in resolved), Decimal("0"))
    if abs(total) > _TOLERANCE:
        raise ClearingError(f"selected items do not net to zero (net {total})")

    clearing = Clearing(client_code=client_code, description=description, cleared_by=actor_id)
    session.add(clearing)
    await session.flush()
    for r in resolved:
        session.add(ClearingItem(clearing_id=clearing.id, module=r.module, record_id=r.record_id, amount=r.amount))
    return clearing


async def reverse_clearing(session: AsyncSession, clearing_id: uuid.UUID) -> Clearing:
    clearing = (await session.execute(select(Clearing).where(Clearing.id == clearing_id))).scalar_one_or_none()
    if clearing is None:
        raise LookupError(f"clearing not found: {clearing_id}")
    if clearing.status != "active":
        raise ClearingError(f"clearing is already '{clearing.status}'")
    clearing.status = "reversed"
    return clearing
