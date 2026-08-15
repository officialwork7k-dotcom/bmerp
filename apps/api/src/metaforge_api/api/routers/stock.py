"""Read-only surface over the stock ledger engine (see
infrastructure/stock.py) — engine-owned tables, not a Builder module, same
reasoning as gl.py.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUserDep, DbSession, Registry
from metaforge_api.infrastructure import stock
from metaforge_api.infrastructure.models import StockMovement

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/valuation")
async def valuation(session: DbSession, registry: Registry, user: CurrentUserDep):
    return await stock.valuation_report(session, registry, client_code=user.client_code)


@router.get("/balance/{item_module}/{item_id}")
async def get_balance(item_module: str, item_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    balance = await stock.get_balance(session, item_module=item_module, item_id=item_id, client_code=user.client_code)
    return {"item_module": item_module, "item_id": str(item_id), "on_hand_qty": float(balance["on_hand_qty"]), "avg_cost": float(balance["avg_cost"])}


@router.get("/movements/{item_module}/{item_id}")
async def list_movements(item_module: str, item_id: uuid.UUID, session: DbSession, user: CurrentUserDep, limit: int = 50):
    query = (
        select(StockMovement)
        .where(
            StockMovement.client_code == user.client_code,
            StockMovement.item_module == item_module,
            StockMovement.item_id == item_id,
        )
        .order_by(StockMovement.created_at.desc())
        .limit(min(limit, 200))
    )
    rows = (await session.execute(query)).scalars().all()
    return [
        {
            "id": str(m.id),
            "movement_type": m.movement_type,
            "quantity": float(m.quantity),
            "unit_cost": float(m.unit_cost) if m.unit_cost is not None else None,
            "resulting_qty": float(m.resulting_qty),
            "resulting_avg_cost": float(m.resulting_avg_cost),
            "document_module": m.document_module,
            "document_id": str(m.document_id) if m.document_id else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]
