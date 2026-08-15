"""Straight-line monthly asset depreciation — the first real consumer of
infrastructure/periodic_runs.py's register_run() pattern (see that
module's docstring for why this runs synchronously, no ARQ).

Depreciates every active fixed_assets record by (cost - salvage) /
useful_life_months, capped at the asset's remaining depreciable base, and
posts ONE journal entry per run covering every asset depreciated in it
(Dr Depreciation Expense / Cr Accumulated Depreciation per asset, using
each asset's own configured GL accounts) — not a per-asset entry, since
nothing in this batch corresponds to a single triggering document the way
posting.py's per-document entries do.

Importing this module registers the run type as a side effect (see the
`@register_run` decorator) — it must be imported somewhere reachable at
app startup (see api/main.py) purely so that import happens, even though
nothing here is called directly from there.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.infrastructure import posting
from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import JournalEntry, JournalLine
from metaforge_api.infrastructure.module_registry import SessionModuleRegistry
from metaforge_api.infrastructure.periodic_runs import register_run
from metaforge_api.infrastructure.repository import DataRepository


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


async def _resolve_asset_accounts(
    session: AsyncSession, registry: SessionModuleRegistry, client_code: str | None, asset_row: dict[str, Any]
) -> tuple[tuple[str, str], tuple[str, str]]:
    """Returns `((expense_code, expense_name), (accum_code, accum_name))` —
    always the *real* gl_accounts name for whichever code was actually
    resolved, never a hardcoded literal. journal_lines.account_name is part
    of trial_balance()'s GROUP BY key; the same account_code posted under
    two different name strings (e.g. a literal "Depreciation Expense" vs.
    the master record's real name for that code) silently splits one
    account into two trial-balance rows and drops part of its balance — a
    real bug this fixes, not just a cosmetic one.

    Per-asset override fields (`gl_depreciation_expense_account`/
    `gl_accum_depreciation_account`, plain TEXT) win if set — an individual
    asset can always be pinned to a specific account. Otherwise resolve via
    the asset's `category` against `asset_categories` (the admin-configured
    per-category subledger mapping), then fall back to the global
    DEPRECIATION_EXPENSE/ACCUM_DEPRECIATION determination rows."""
    expense_override = asset_row.get("gl_depreciation_expense_account")
    accum_override = asset_row.get("gl_accum_depreciation_account")
    expense_code = str(expense_override) if expense_override else None
    accum_code = str(accum_override) if accum_override else None

    category = asset_row.get("category")
    if category and not (expense_code and accum_code):
        cat_table = resolve_table(registry.get("asset_categories"), registry)
        cat_row = (
            await session.execute(select(cat_table).where(cat_table.c.category == category, cat_table.c.deleted_at.is_(None)))
        ).mappings().first()
        if cat_row:
            if not expense_code and cat_row.get("depreciation_expense_gl_account_id"):
                expense_code, _ = await posting._gl_account_by_id(session, registry, cat_row["depreciation_expense_gl_account_id"])
            if not accum_code and cat_row.get("accum_depreciation_gl_account_id"):
                accum_code, _ = await posting._gl_account_by_id(session, registry, cat_row["accum_depreciation_gl_account_id"])

    if not expense_code:
        expense_code, _ = await posting._resolve_determination_account(session, registry, client_code, "DEPRECIATION_EXPENSE")
    if not accum_code:
        accum_code, _ = await posting._resolve_determination_account(session, registry, client_code, "ACCUM_DEPRECIATION")

    # Whatever code we landed on (override, category, or determination
    # fallback), always look up its *real* name — a per-asset override is a
    # plain TEXT code with no guaranteed matching gl_accounts row, so this
    # tolerates that the same way `_gl_account_by_code` does elsewhere.
    _, expense_name = await posting._gl_account_by_code(session, registry, expense_code)
    _, accum_name = await posting._gl_account_by_code(session, registry, accum_code)
    return (expense_code, expense_name), (accum_code, accum_name)


@register_run("asset_depreciation")
async def run_depreciation(
    session: AsyncSession, *, client_code: str | None, period_key: str,
    actor_id: uuid.UUID | None, run_id: uuid.UUID, **kwargs: Any
) -> dict[str, Any]:
    registry = SessionModuleRegistry()
    await registry.load_all(session)
    repo = DataRepository(session, registry, client_code=client_code)

    module = registry.get("fixed_assets")
    table = resolve_table(module, registry)
    query = select(table).where(table.c.deleted_at.is_(None), table.c.status == "active")
    if client_code is not None and "client_code" in table.c:
        query = query.where(table.c.client_code == client_code)
    rows = (await session.execute(query)).mappings().all()

    postings: list[tuple[tuple[str, str], tuple[str, str], Decimal]] = []  # ((expense_code, expense_name), (accum_code, accum_name), amount)
    processed = 0
    total = Decimal("0")

    for row in rows:
        cost = _to_decimal(row.get("acquisition_cost"))
        salvage = _to_decimal(row.get("salvage_value"))
        life = row.get("useful_life_months") or 0
        if life <= 0:
            continue
        depreciable_base = cost - salvage
        accumulated = _to_decimal(row.get("accumulated_depreciation"))
        remaining = depreciable_base - accumulated
        if remaining <= 0:
            continue
        amount = min(depreciable_base / life, remaining)
        if amount <= 0:
            continue

        await repo.update(
            "fixed_assets", row["id"],
            {"accumulated_depreciation": accumulated + amount, "version": row["version"]},
            actor_id=actor_id,
        )
        expense_account, accum_account = await _resolve_asset_accounts(session, registry, client_code, dict(row))
        postings.append((expense_account, accum_account, amount))
        processed += 1
        total += amount

    if not postings:
        return {"assets_processed": 0, "total_depreciation": 0.0}

    year, month = (int(p) for p in period_key.split("-"))
    entry = JournalEntry(
        client_code=client_code,
        document_module="periodic_runs",
        document_id=run_id,
        posting_date=date(year, month, 1),
        description=f"Depreciation run {period_key}",
        status="posted",
        posted_by=actor_id,
    )
    session.add(entry)
    await session.flush()
    line_no = 1
    for (expense_code, expense_name), (accum_code, accum_name), amount in postings:
        session.add(JournalLine(
            journal_entry_id=entry.id, line_no=line_no, account_code=expense_code,
            account_name=expense_name, debit=amount, credit=Decimal("0"),
        ))
        line_no += 1
        session.add(JournalLine(
            journal_entry_id=entry.id, line_no=line_no, account_code=accum_code,
            account_name=accum_name, debit=Decimal("0"), credit=amount,
        ))
        line_no += 1

    return {"assets_processed": processed, "total_depreciation": float(total), "journal_entry_id": str(entry.id)}
