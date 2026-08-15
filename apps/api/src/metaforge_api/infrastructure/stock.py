"""Stock/quantity ledger engine — same architectural pattern as
posting.py, for quantities instead of money: an append-only stock_movements
ledger, with on-hand quantity and moving-average cost held on a locked
stock_balances row (SELECT ... FOR UPDATE, same locking pattern already
used for AUTO_NUMBER allocation) so two concurrent movements against the
same item can never race — the row lock serializes them.

Not a Builder module: on-hand quantity is derived state, not something a
form should ever let a user type directly into (that's exactly the
"quantity ledger" invariant this engine exists to enforce).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.metadata import ModuleMetadata
from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import StockBalance, StockMovement


class StockError(Exception):
    pass


class _Registry(Protocol):
    def get(self, name: str) -> ModuleMetadata: ...


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


async def post_movement(
    session: AsyncSession,
    *,
    item_module: str,
    item_id: uuid.UUID,
    quantity: Decimal,
    movement_type: str,
    unit_cost: Decimal | None = None,
    client_code: str | None,
    actor_id: uuid.UUID | None,
    document_module: str | None = None,
    document_id: uuid.UUID | None = None,
) -> StockMovement:
    """`quantity` is signed: positive increases on-hand (receipt), negative
    decreases it (issue). Raises StockError rather than allowing on-hand to
    go negative — no backorder/negative-stock support in this core."""
    if quantity == 0:
        raise StockError("movement quantity must be non-zero")

    balance = (
        await session.execute(
            select(StockBalance)
            .where(StockBalance.client_code == client_code, StockBalance.item_module == item_module, StockBalance.item_id == item_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if balance is None:
        # First movement for this item: nothing to lock yet, and nothing
        # concurrent can be racing us for a row that doesn't exist —
        # inserting it here establishes it atomically within this
        # transaction (a concurrent insert would hit the unique constraint
        # and the loser would retry, same tradeoff as number_series).
        balance = StockBalance(client_code=client_code, item_module=item_module, item_id=item_id)
        session.add(balance)
        await session.flush()

    new_qty = balance.on_hand_qty + quantity
    if new_qty < 0:
        raise StockError(
            f"insufficient stock for {item_module}/{item_id}: on-hand {balance.on_hand_qty}, requested {quantity}"
        )

    if quantity > 0 and unit_cost is not None:
        # Weighted moving average: blend the incoming cost into the
        # existing on-hand value. Issues/adjustments never move the
        # average — only a priced receipt does.
        prior_value = balance.on_hand_qty * balance.avg_cost
        incoming_value = quantity * unit_cost
        new_avg = (prior_value + incoming_value) / new_qty if new_qty != 0 else Decimal("0")
    else:
        new_avg = balance.avg_cost

    balance.on_hand_qty = new_qty
    balance.avg_cost = new_avg

    movement = StockMovement(
        client_code=client_code,
        item_module=item_module,
        item_id=item_id,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=unit_cost,
        resulting_qty=new_qty,
        resulting_avg_cost=new_avg,
        document_module=document_module,
        document_id=document_id,
        created_by=actor_id,
    )
    session.add(movement)
    return movement


async def get_balance(session: AsyncSession, *, item_module: str, item_id: uuid.UUID, client_code: str | None) -> dict[str, Any]:
    balance = (
        await session.execute(
            select(StockBalance).where(
                StockBalance.client_code == client_code, StockBalance.item_module == item_module, StockBalance.item_id == item_id
            )
        )
    ).scalar_one_or_none()
    if balance is None:
        return {"on_hand_qty": Decimal("0"), "avg_cost": Decimal("0")}
    return {"on_hand_qty": balance.on_hand_qty, "avg_cost": balance.avg_cost}


_LABEL_SKIP = {"id", "created_at", "updated_at", "created_by", "deleted_at", "version", "client_code"}


async def valuation_report(session: AsyncSession, registry: _Registry, *, client_code: str | None) -> dict[str, Any]:
    """Every item with a nonzero on-hand quantity, valued at its current
    moving-average cost — the "what stock do we hold and what is it worth"
    report a trial balance's Inventory line can't answer on its own.
    `item_module` is generic per StockBalance's own docstring, so this
    resolves each item's display label generically too (first non-system
    field on its own row), the same heuristic `labelOf()` uses client-side."""
    from metaforge_api.infrastructure.dynamic_tables import resolve_table

    query = select(StockBalance).where(StockBalance.on_hand_qty != 0)
    if client_code is not None:
        query = query.where(StockBalance.client_code == client_code)
    balances = (await session.execute(query)).scalars().all()

    rows: list[dict[str, Any]] = []
    total_value = Decimal("0")
    tables_cache: dict[str, Any] = {}
    for b in balances:
        item_module_name = b.item_module
        if item_module_name not in tables_cache:
            try:
                tables_cache[item_module_name] = resolve_table(registry.get(item_module_name), registry)
            except KeyError:
                tables_cache[item_module_name] = None
        table = tables_cache[item_module_name]
        label = str(b.item_id)
        if table is not None:
            item_row = (await session.execute(select(table).where(table.c.id == b.item_id))).mappings().first()
            if item_row:
                key = next((k for k in item_row.keys() if k not in _LABEL_SKIP and not k.endswith("_id")), None)
                if key:
                    label = str(item_row[key])
        value = b.on_hand_qty * b.avg_cost
        rows.append(
            {
                "item_module": item_module_name,
                "item_id": str(b.item_id),
                "item_label": label,
                "on_hand_qty": float(b.on_hand_qty),
                "avg_cost": float(b.avg_cost),
                "value": float(value),
            }
        )
        total_value += value

    rows.sort(key=lambda r: r["item_label"])
    return {"rows": rows, "total_value": float(total_value)}


async def apply_stock_rules(
    session: AsyncSession, module: ModuleMetadata, record: dict[str, Any], registry: _Registry, *,
    client_code: str | None, actor_id: uuid.UUID | None,
) -> list[StockMovement]:
    """Called from repository.transition() alongside posting.post_document
    — walks module.stock_rules the same way posting_rules' "per_child" line
    type walks an embedded relationship's rows."""
    rules = module.stock_rules
    if not rules:
        return []
    movements = []
    for rule in rules.get("lines", []):
        # `child_relation` is optional: most modules post one movement per
        # embedded line (a GR/Delivery's line items), but a "header-is-the-
        # line" module like stock_adjustments has nothing to walk — the
        # record itself is the one row to post.
        if rule.get("child_relation"):
            rel = next((r for r in module.embedded_children() if r.name == rule["child_relation"]), None)
            if rel is None:
                raise StockError(f"stock rule references unknown embedded relationship '{rule['child_relation']}'")
            child_module = registry.get(rel.related_module)
            child_table = resolve_table(child_module, registry)
            rows = (
                await session.execute(
                    select(child_table).where(child_table.c[rel.foreign_key] == record["id"], child_table.c.deleted_at.is_(None))
                )
            ).mappings().all()
        else:
            rows = [record]

        item_field = rule["item_field"]
        qty_field = rule["qty_field"]
        cost_field = rule.get("unit_cost_field")
        direction = 1 if rule.get("direction", "in") == "in" else -1
        item_module_meta = registry.get(rule["item_module"])
        item_table = resolve_table(item_module_meta, registry) if item_module_meta.field("item_type") else None

        # Landed-cost apportionment: a header-level charges relation (e.g.
        # freight, duty, handling on a Goods Receipt) gets spread pro-rata
        # across this rule's lines by line value (qty * unit_cost) and
        # folded into each line's *effective* unit cost for the stock
        # movement — the moving-average cost captures the landed cost, not
        # just the agreed PO/line price. The stored `unit_cost_field` on the
        # line itself is left untouched (it's the negotiated price, not
        # something a freight allocation should silently rewrite).
        cost_adjustment_per_unit: dict[Any, Decimal] = {}
        charges_rel_name = rule.get("charges_relation")
        if charges_rel_name and cost_field:
            charges_rel = next((r for r in module.embedded_children() if r.name == charges_rel_name), None)
            if charges_rel is not None:
                charges_module = registry.get(charges_rel.related_module)
                charges_table = resolve_table(charges_module, registry)
                charges_amount_field = rule.get("charges_amount_field", "amount")
                charge_rows = (
                    await session.execute(
                        select(charges_table).where(
                            charges_table.c[charges_rel.foreign_key] == record["id"], charges_table.c.deleted_at.is_(None)
                        )
                    )
                ).mappings().all()
                total_charges = sum((_to_decimal(c.get(charges_amount_field)) for c in charge_rows), Decimal("0"))
                if total_charges > 0:
                    line_values = {r["id"]: _to_decimal(r.get(qty_field)) * _to_decimal(r.get(cost_field)) for r in rows}
                    total_value = sum(line_values.values(), Decimal("0"))
                    if total_value > 0:
                        for row in rows:
                            qty = _to_decimal(row.get(qty_field))
                            if qty == 0:
                                continue
                            share = total_charges * (line_values[row["id"]] / total_value)
                            cost_adjustment_per_unit[row["id"]] = share / qty

        for row in rows:
            item_id = row.get(item_field)
            if not item_id:
                continue
            # A freight/service charge selected as a line item (any other
            # module field references the same Items master a stocked
            # material would) must never move inventory quantity — only a
            # STOCK item receipt/issue affects on-hand. It still flows
            # through posting_rules normally (that's driven by line_total,
            # not item_type), just not through the quantity ledger.
            if item_table is not None:
                item_uuid = item_id if isinstance(item_id, uuid.UUID) else uuid.UUID(str(item_id))
                item_type = (
                    await session.execute(select(item_table.c.item_type).where(item_table.c.id == item_uuid))
                ).scalar_one_or_none()
                if item_type == "SERVICE":
                    continue
            qty = _to_decimal(row.get(qty_field)) * direction
            if qty == 0:
                continue
            unit_cost = _to_decimal(row.get(cost_field)) if cost_field else None
            if unit_cost is not None and direction > 0:
                unit_cost += cost_adjustment_per_unit.get(row["id"], Decimal("0"))
            # Movement type: a fixed `movement_type` on the rule (e.g. every
            # Delivery line is a "delivery_issue"), or a per-row field for
            # modules where the user picks the type themselves (e.g.
            # stock_adjustments' own `movement_type` ENUM distinguishing a
            # production issue from a plain count correction), falling back
            # to the generic in/out label so older rule configs keep working
            # unchanged.
            movement_type_field = rule.get("movement_type_field")
            movement_type = (
                rule.get("movement_type")
                or (row.get(movement_type_field) if movement_type_field else None)
                or ("receipt" if direction > 0 else "issue")
            )
            movement = await post_movement(
                session,
                item_module=rule["item_module"],
                item_id=item_id if isinstance(item_id, uuid.UUID) else uuid.UUID(str(item_id)),
                quantity=qty,
                movement_type=movement_type,
                unit_cost=unit_cost,
                client_code=client_code,
                actor_id=actor_id,
                document_module=module.name,
                document_id=record["id"],
            )
            movements.append(movement)
    return movements
