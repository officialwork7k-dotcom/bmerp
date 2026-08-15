"""Price-list resolution: the minimal "most specific match wins" pattern —
party + item + quantity-break, optionally date-bounded — deliberately not
SAP's full condition-technique. Price lists themselves are plain Builder
modules (e.g. vendor_price_lists/customer_price_lists); this is just the
one bit of resolution logic a form can't express declaratively.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter
from sqlalchemy import and_, or_, select

from metaforge_api.api.deps import CurrentUserDep, Registry, Repository
from metaforge_api.infrastructure.dynamic_tables import resolve_table

router = APIRouter(prefix="/api/price-lists", tags=["price-lists"])


@router.get("/resolve")
async def resolve_price(
    price_list_module: str,
    party_field: str,
    party_id: uuid.UUID,
    item_field: str,
    item_id: uuid.UUID,
    qty: float,
    repo: Repository,
    registry: Registry,
    user: CurrentUserDep,
):
    """Returns the best-matching price list row's unit_price/discount_pct
    for this party+item+qty, or null if nothing matches. "Best" = active,
    within any configured valid_from/valid_to window, qty at or above the
    row's min_qty — ties broken by the highest min_qty (the most specific
    quantity break that still qualifies)."""
    module = registry.get(price_list_module)
    table = resolve_table(module, registry)
    today = date.today()

    conditions = [
        table.c[party_field] == party_id,
        table.c[item_field] == item_id,
        table.c.deleted_at.is_(None),
    ]
    if "min_qty" in table.c:
        conditions.append(table.c.min_qty <= qty)
    if "is_active" in table.c:
        conditions.append(table.c.is_active.is_(True))
    if "valid_from" in table.c:
        conditions.append(or_(table.c.valid_from.is_(None), table.c.valid_from <= today))
    if "valid_to" in table.c:
        conditions.append(or_(table.c.valid_to.is_(None), table.c.valid_to >= today))
    if repo.client_code is not None and "client_code" in table.c:
        conditions.append(table.c.client_code == repo.client_code)

    query = select(table).where(and_(*conditions))
    if "min_qty" in table.c:
        query = query.order_by(table.c.min_qty.desc())
    query = query.limit(1)

    row = (await repo.session.execute(query)).mappings().first()
    if row is None:
        return None
    return {
        "unit_price": float(row["unit_price"]) if row.get("unit_price") is not None else None,
        "discount_pct": float(row["discount_pct"]) if row.get("discount_pct") is not None else None,
    }
