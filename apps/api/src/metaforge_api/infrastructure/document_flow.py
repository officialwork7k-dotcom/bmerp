"""Document flow / copy-with-reference engine: generates a follow-on
document (a Goods Receipt from a Purchase Order, a Customer Invoice from a
Delivery) pre-populated from a source document, tracking per-source-line
how much has already been copied forward so the same PO line can't be
over-receipted past its ordered quantity (within a configurable tolerance).

Metadata-driven (ModuleMetadata.document_flows on the *source* module), not
a Builder module itself — the copy operation's "how much is still open"
bookkeeping (document_flow_links) is algorithmic state a form can't own.

Reuses DataRepository.create() to actually build the target document, so
every existing invariant (client-code scoping, number-series allocation,
SoD, fiscal-period gate, audit trail, aggregates) applies to a copied
document exactly as it would to one a user typed in by hand — this engine
only computes *what* to copy, not how to write it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.metadata import ModuleMetadata
from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import DocumentFlowLink
from metaforge_api.infrastructure.repository import ChildDiff


class DocumentFlowError(Exception):
    pass


class ThreeWayMatchError(Exception):
    pass


class _Registry(Protocol):
    def get(self, name: str) -> ModuleMetadata: ...


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _find_flow(module: ModuleMetadata, flow_name: str) -> dict:
    for flow in module.document_flows or []:
        if flow["name"] == flow_name:
            return flow
    raise DocumentFlowError(f"module '{module.name}' has no document flow named '{flow_name}'")


async def open_quantity(session: AsyncSession, source_module: str, source_line_id: uuid.UUID, total_qty: Decimal) -> Decimal:
    copied = (
        await session.execute(
            select(func.coalesce(func.sum(DocumentFlowLink.qty), 0)).where(
                DocumentFlowLink.source_module == source_module, DocumentFlowLink.source_line_id == source_line_id
            )
        )
    ).scalar_one()
    return total_qty - Decimal(str(copied))


async def check_three_way_match(session: AsyncSession, registry: _Registry, module: ModuleMetadata, record_id: uuid.UUID) -> None:
    """The other half of the tolerance_pct config a document flow already
    enforces at copy time: that check only ever stops a copy from
    *creating* an over-quantity line. Nothing stopped someone from pulling
    lines in, then hand-editing the qty up (or a source PO line being
    over-matched by two different partial invoices) before saving — the
    line just silently drifted past what was actually ordered/received.
    Called at the point a document transitions into a locked state (i.e.
    "posted"): re-checks every line that traces back to a document-flow
    copy against the source line's *current* remaining-open quantity,
    across every other target it's also been copied to, using the same
    tolerance the flow was configured with. Raises rather than silently
    truncating — the classic three-way match (PO/GR/Invoice) is a hard
    stop, not a rounding adjustment."""
    links = (
        await session.execute(select(DocumentFlowLink).where(DocumentFlowLink.target_document_id == record_id))
    ).scalars().all()
    if not links:
        return

    for link in links:
        source_module = registry.get(link.source_module)
        flow = next((f for f in source_module.document_flows or [] if f.get("target_module") == module.name), None)
        if flow is None:
            continue
        tolerance = Decimal(str(flow.get("tolerance_pct", 0))) / Decimal("100")

        source_rel = next((r for r in source_module.embedded_children() if r.name == flow["source_line_relation"]), None)
        if source_rel is None:
            continue
        source_table = resolve_table(registry.get(source_rel.related_module), registry)
        source_line = (await session.execute(select(source_table).where(source_table.c.id == link.source_line_id))).mappings().first()
        if source_line is None:
            continue
        total_qty = _to_decimal(source_line.get(flow["source_qty_field"]))

        other_links_qty = (
            await session.execute(
                select(func.coalesce(func.sum(DocumentFlowLink.qty), 0)).where(
                    DocumentFlowLink.source_module == link.source_module,
                    DocumentFlowLink.source_line_id == link.source_line_id,
                    DocumentFlowLink.id != link.id,
                )
            )
        ).scalar_one()

        target_rel = next((r for r in module.embedded_children() if r.name == flow["target_line_relation"]), None)
        if target_rel is None:
            continue
        target_table = resolve_table(registry.get(target_rel.related_module), registry)
        target_line = (await session.execute(select(target_table).where(target_table.c.id == link.target_line_id))).mappings().first()
        if target_line is None:
            continue
        current_qty = _to_decimal(target_line.get(flow["target_qty_field"]))

        max_allowed = (total_qty - Decimal(str(other_links_qty))) * (1 + tolerance)
        if current_qty > max_allowed:
            raise ThreeWayMatchError(
                f"three-way match failed: {module.name} line quantity {current_qty} exceeds the matched "
                f"{link.source_module} line's remaining quantity {max_allowed} (tolerance {flow.get('tolerance_pct', 0)}%)"
            )


@dataclass
class _LineResult:
    source_line_id: uuid.UUID
    qty: Decimal
    target_line_data: dict[str, Any]


async def _require_same_org(
    session: AsyncSession, source_table, source_id: uuid.UUID, client_code: str | None, source_module_name: str
) -> None:
    """A document-flow source_id arrives as a raw UUID in an API payload —
    same risk repository._validate_lookup_scope guards against on LOOKUP
    fields, but this engine reads the source record directly rather than
    through a LOOKUP, so it needs its own check. Without it, a caller could
    "pull lines" from — or preview/copy against — another org's Purchase
    Order/Goods Receipt/Delivery entirely, reading (and in copy_document's
    case, writing derived data from) a document outside their tenant."""
    if client_code is None or "client_code" not in source_table.c:
        return
    row = (
        await session.execute(
            select(source_table.c.id).where(source_table.c.id == source_id, source_table.c.client_code == client_code)
        )
    ).first()
    if row is None:
        raise LookupError(f"record not found: {source_module_name}/{source_id}")


async def open_lines(
    session: AsyncSession, registry: _Registry, source_module_name: str, source_id: uuid.UUID, flow_name: str,
    *, client_code: str | None = None,
) -> list[dict[str, Any]]:
    """What a caller can still copy forward for this source document — the
    listing an admin/clerk would see before picking what to include in a
    follow-on document."""
    module = registry.get(source_module_name)
    flow = _find_flow(module, flow_name)
    await _require_same_org(session, resolve_table(module, registry), source_id, client_code, source_module_name)
    rel = next((r for r in module.embedded_children() if r.name == flow["source_line_relation"]), None)
    if rel is None:
        raise DocumentFlowError(f"unknown embedded relationship '{flow['source_line_relation']}'")
    child_table = resolve_table(registry.get(rel.related_module), registry)
    rows = (
        await session.execute(
            select(child_table).where(child_table.c[rel.foreign_key] == source_id, child_table.c.deleted_at.is_(None))
        )
    ).mappings().all()

    qty_field = flow["source_qty_field"]
    result = []
    for row in rows:
        total_qty = _to_decimal(row.get(qty_field))
        remaining = await open_quantity(session, source_module_name, row["id"], total_qty)
        result.append({"line_id": str(row["id"]), "total_qty": float(total_qty), "open_qty": float(remaining)})
    return result


@dataclass
class _ResolvedCopy:
    header_data: dict[str, Any]
    lines: list[_LineResult]
    # Untracked child relations copied alongside `lines` — e.g. a GR's
    # freight/other-charges rows carried into the Vendor Invoice it's
    # pulled into. Unlike `lines`, these have no qty/three-way-match
    # bookkeeping: every open row on the source relation is copied in full
    # every time (a charge isn't "partially fulfilled" the way an ordered
    # quantity is), keyed by the *target* relation name.
    extra: dict[str, list[dict[str, Any]]]


async def _resolve_extra_relations(
    session: AsyncSession, registry: _Registry, module: ModuleMetadata, flow: dict, source: Any,
) -> dict[str, list[dict[str, Any]]]:
    extra: dict[str, list[dict[str, Any]]] = {}
    for spec in flow.get("extra_relations", []):
        rel = next((r for r in module.embedded_children() if r.name == spec["source_relation"]), None)
        if rel is None:
            continue
        child_table = resolve_table(registry.get(rel.related_module), registry)
        rows = (
            await session.execute(
                select(child_table).where(child_table.c[rel.foreign_key] == source["id"], child_table.c.deleted_at.is_(None))
            )
        ).mappings().all()
        extra[spec["target_relation"]] = [
            {target_field: row.get(source_field) for source_field, target_field in spec.get("field_map", {}).items()}
            for row in rows
        ]
    return extra


async def _resolve_copy(
    session: AsyncSession,
    registry: _Registry,
    source_module_name: str,
    source_id: uuid.UUID,
    flow_name: str,
    *,
    line_selections: list[dict[str, Any]] | None,
    client_code: str | None = None,
) -> _ResolvedCopy:
    """The pure "what would this copy produce" computation — no writes.
    Shared by `copy_document` (persists the result) and `preview_copy` (just
    shows the caller what would be copied, e.g. so a Vendor Invoice form can
    offer "pull lines from this GR" before the invoice itself even exists
    yet as a saved record)."""
    module = registry.get(source_module_name)
    flow = _find_flow(module, flow_name)
    source_table = resolve_table(module, registry)
    await _require_same_org(session, source_table, source_id, client_code, source_module_name)
    source = (await session.execute(select(source_table).where(source_table.c.id == source_id))).mappings().first()
    if source is None:
        raise LookupError(f"record not found: {source_module_name}/{source_id}")

    rel = next((r for r in module.embedded_children() if r.name == flow["source_line_relation"]), None)
    if rel is None:
        raise DocumentFlowError(f"unknown embedded relationship '{flow['source_line_relation']}'")
    child_module = registry.get(rel.related_module)
    child_table = resolve_table(child_module, registry)
    source_lines = {
        row["id"]: row
        for row in (
            await session.execute(
                select(child_table).where(child_table.c[rel.foreign_key] == source_id, child_table.c.deleted_at.is_(None))
            )
        ).mappings().all()
    }
    if not source_lines:
        raise DocumentFlowError(f"{source_module_name}/{source_id} has no lines to copy")

    qty_field = flow["source_qty_field"]
    target_qty_field = flow["target_qty_field"]
    tolerance = Decimal(str(flow.get("tolerance_pct", 0))) / Decimal("100")

    requested = line_selections or [{"source_line_id": str(lid)} for lid in source_lines]

    resolved: list[_LineResult] = []
    for sel in requested:
        line_id = sel["source_line_id"] if isinstance(sel["source_line_id"], uuid.UUID) else uuid.UUID(str(sel["source_line_id"]))
        source_line = source_lines.get(line_id)
        if source_line is None:
            raise DocumentFlowError(f"line {line_id} does not belong to {source_module_name}/{source_id}")
        total_qty = _to_decimal(source_line.get(qty_field))
        remaining = await open_quantity(session, source_module_name, line_id, total_qty)
        qty = _to_decimal(sel["qty"]) if "qty" in sel and sel["qty"] is not None else remaining
        if qty <= 0:
            continue
        max_allowed = remaining * (1 + tolerance)
        if qty > max_allowed:
            raise DocumentFlowError(
                f"line {line_id}: requested {qty} exceeds open quantity {remaining} (tolerance {flow.get('tolerance_pct', 0)}%)"
            )
        target_line_data = {
            target_field: source_line.get(source_field) for source_field, target_field in flow.get("line_field_map", {}).items()
        }
        target_line_data[target_qty_field] = qty
        resolved.append(_LineResult(source_line_id=line_id, qty=qty, target_line_data=target_line_data))

    if not resolved:
        raise DocumentFlowError("nothing to copy — every selected line is already fully fulfilled")

    header_data = {target_field: source.get(source_field) for source_field, target_field in flow.get("header_field_map", {}).items()}
    extra = await _resolve_extra_relations(session, registry, module, flow, source)
    return _ResolvedCopy(header_data=header_data, lines=resolved, extra=extra)


async def preview_copy(
    session: AsyncSession, registry: _Registry, source_module_name: str, source_id: uuid.UUID, flow_name: str,
    *, client_code: str | None = None,
) -> dict[str, Any]:
    """Same computation `copy_document` would persist, minus the write —
    lets a form show what pulling lines from this source would produce
    before the target record is ever saved."""
    resolved = await _resolve_copy(session, registry, source_module_name, source_id, flow_name, line_selections=None, client_code=client_code)
    return {
        "header": _jsonable_preview(resolved.header_data),
        "lines": [_jsonable_preview(r.target_line_data) for r in resolved.lines],
        "extra": {rel: [_jsonable_preview(row) for row in rows] for rel, rows in resolved.extra.items()},
    }


def _jsonable_preview(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif isinstance(v, Decimal):
            out[k] = float(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def flows_into(registry_all: dict[str, ModuleMetadata], target_module: str) -> list[dict[str, Any]]:
    """Reverse index: every document flow across all modules whose
    `target_module` matches — lets a form (e.g. Vendor Invoice) discover
    "goods_receipts has a flow that lands here, triggered when its gr_id
    LOOKUP field is picked" without hand-wiring the relationship per pair
    of modules."""
    out = []
    for module in registry_all.values():
        for flow in module.document_flows or []:
            if flow.get("target_module") == target_module:
                out.append(
                    {
                        "source_module": module.name,
                        "flow_name": flow["name"],
                        "header_field_map": flow.get("header_field_map", {}),
                        "target_line_relation": flow.get("target_line_relation"),
                    }
                )
    return out


async def copy_document(
    session: AsyncSession,
    registry: _Registry,
    repository: Any,  # DataRepository — typed loosely to avoid a circular import
    source_module_name: str,
    source_id: uuid.UUID,
    flow_name: str,
    *,
    line_selections: list[dict[str, Any]] | None,
    actor_id: uuid.UUID | None,
) -> dict[str, Any]:
    """`line_selections` is `[{"source_line_id": ..., "qty": ...}, ...]` —
    omit (None) to copy every source line's full remaining open quantity.
    Raises DocumentFlowError if a requested qty exceeds what's open (plus
    tolerance)."""
    resolved_copy = await _resolve_copy(
        session, registry, source_module_name, source_id, flow_name,
        line_selections=line_selections, client_code=repository.client_code,
    )
    header_data = resolved_copy.header_data
    resolved = resolved_copy.lines
    flow = _find_flow(registry.get(source_module_name), flow_name)
    target_line_rel = flow["target_line_relation"]

    children = {target_line_rel: ChildDiff(create=[r.target_line_data for r in resolved])}
    for rel_name, rows in resolved_copy.extra.items():
        children[rel_name] = ChildDiff(create=rows)

    target = await repository.create(
        flow["target_module"],
        header_data,
        children,
        actor_id=actor_id,
    )

    # Match the newly created target lines back to the source lines they
    # came from, positionally — safe here because _apply_children inserts
    # diff.create rows in list order within this same transaction, and
    # uuidv7 ids sort by creation time, so ordering by id recovers exactly
    # the order they were submitted in.
    target_module = registry.get(flow["target_module"])
    target_child_module = registry.get(next(r.related_module for r in target_module.embedded_children() if r.name == target_line_rel))
    target_fk = next(r.foreign_key for r in target_module.embedded_children() if r.name == target_line_rel)
    target_child_table = resolve_table(target_child_module, registry)
    new_lines = (
        await session.execute(
            select(target_child_table.c.id).where(target_child_table.c[target_fk] == target["id"]).order_by(target_child_table.c.id)
        )
    ).scalars().all()

    for target_line_id, r in zip(new_lines, resolved):
        session.add(
            DocumentFlowLink(
                client_code=getattr(repository, "client_code", None),
                source_module=source_module_name,
                source_line_id=r.source_line_id,
                target_module=flow["target_module"],
                target_line_id=target_line_id,
                target_document_id=target["id"],
                qty=r.qty,
                created_by=actor_id,
            )
        )

    return target
