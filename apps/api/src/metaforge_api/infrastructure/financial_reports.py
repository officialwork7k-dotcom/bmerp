"""Financial statement reports — trial balance, AR/AP aging, vendor/customer
ledgers — built entirely on data two existing engines already produce
(posting.py's journal_entries/journal_lines, clearing.py's clearing_config)
plus a small Builder module (`opening_balances`) for brought-forward
balances. No new engine-owned tables here.

Deliberately generic over `ModuleMetadata.clearing_config` rather than
hardcoding module names: any clearing-enabled module tagged with a `group`
("AP"|"AR") and a `party_module` (which module its `party_field` LOOKUP
points at) automatically participates in aging/ledger reports — a future
AP-like module (e.g. "bank charges payable") only needs its own
clearing_config to show up here, no code change.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.metadata import FieldDataType, ModuleMetadata
from metaforge_api.infrastructure import clearing
from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import JournalEntry, JournalLine

_GROUP_TO_PARTY_SCOPE = {"AP": "VENDOR", "AR": "CUSTOMER"}


class ReportError(Exception):
    pass


class _Registry(Protocol):
    def get(self, name: str) -> ModuleMetadata: ...
    def all(self) -> dict[str, ModuleMetadata]: ...


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _date_field(module: ModuleMetadata) -> str | None:
    gate = next((f.name for f in module.fields if f.is_period_gate), None)
    if gate:
        return gate
    return "created_at" if any(f.name == "created_at" for f in module.fields) else None


def _label_field(module: ModuleMetadata) -> str | None:
    return next((f.name for f in module.fields if f.data_type == FieldDataType.AUTO_NUMBER), None)


def _group_modules(registry: _Registry, group: str) -> list[ModuleMetadata]:
    return [m for m in registry.all().values() if m.clearing_config and m.clearing_config.get("group") == group]


async def _resolve_party_label(session: AsyncSession, registry: _Registry, party_module: str, party_id: uuid.UUID) -> str:
    module = registry.get(party_module)
    table = resolve_table(module, registry)
    row = (await session.execute(select(table).where(table.c.id == party_id))).mappings().first()
    if row is None:
        return str(party_id)
    skip = {"id", "created_at", "updated_at", "created_by", "deleted_at", "version", "client_code"}
    key = next((k for k in row.keys() if k not in skip and not k.endswith("_id")), None)
    return str(row[key]) if key else str(party_id)


async def trial_balance(
    session: AsyncSession, registry: _Registry, *, client_code: str | None, as_of_date: date,
) -> dict[str, Any]:
    from sqlalchemy import func

    query = (
        select(
            JournalLine.account_code,
            # MAX, not a GROUP BY column: journal_lines snapshots whatever
            # account_name string was current at post time, and two
            # postings to the same account_code months apart can carry
            # slightly different name text (a master-data rename, or — the
            # bug this guards against — a caller that resolved the account
            # correctly but labeled it with a stale/hardcoded name).
            # Grouping by account_code+account_name would silently split
            # one account into two trial-balance rows and drop part of its
            # balance from the total; grouping by account_code alone with
            # MAX(name) for display can't lose money, only pick one of
            # several equally-valid display strings.
            func.max(JournalLine.account_name).label("account_name"),
            func.coalesce(func.sum(JournalLine.debit), 0).label("debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("credit"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        # Both 'posted' AND 'reversed' entries must count here — reverse()
        # never deletes or zeroes the original, it flags it 'reversed' and
        # appends a second entry with every line's debit/credit swapped.
        # The two together net to exactly zero by construction; excluding
        # the original (status == "posted" alone) leaves only the mirror
        # entry standing, which doesn't cancel anything — it *doubles* the
        # correction, silently misstating every account a reversal ever
        # touched (e.g. a wrongly-reversed depreciation run understated
        # Depreciation Expense by 3x the one erroneous period instead of
        # leaving it untouched). 'reversed' is a status label for display
        # ("this posting was superseded"), not a flag for "didn't happen."
        .where(JournalEntry.status.in_(("posted", "reversed")), JournalEntry.posting_date <= as_of_date)
        .group_by(JournalLine.account_code)
    )
    if client_code is not None:
        query = query.where(JournalEntry.client_code == client_code)
    rows = (await session.execute(query)).all()

    balances: dict[str, dict[str, Any]] = {
        r.account_code: {"account_code": r.account_code, "account_name": r.account_name, "debit": _to_decimal(r.debit), "credit": _to_decimal(r.credit)}
        for r in rows
    }

    # Fold in GL-account opening balances for the fiscal year `as_of_date`
    # falls in — a fiscal year here is just the calendar year (matches
    # FiscalPeriod.period_key's "YYYY-MM" convention).
    opening_module = registry.get("opening_balances")
    opening_table = resolve_table(opening_module, registry)
    ob_query = select(opening_table).where(
        opening_table.c.deleted_at.is_(None),
        opening_table.c.scope == "GL_ACCOUNT",
        opening_table.c.fiscal_year == as_of_date.year,
    )
    if client_code is not None and "client_code" in opening_table.c:
        ob_query = ob_query.where(opening_table.c.client_code == client_code)
    for ob in (await session.execute(ob_query)).mappings().all():
        code = ob["gl_account_code"]
        if not code:
            continue
        amount = _to_decimal(ob["amount"])
        entry = balances.setdefault(code, {"account_code": code, "account_name": ob.get("description") or code, "debit": Decimal("0"), "credit": Decimal("0")})
        if amount >= 0:
            entry["debit"] += amount
        else:
            entry["credit"] += -amount

    out = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for entry in sorted(balances.values(), key=lambda e: e["account_code"]):
        debit, credit = entry["debit"], entry["credit"]
        net = debit - credit
        out.append(
            {
                "account_code": entry["account_code"],
                "account_name": entry["account_name"],
                "debit": float(debit),
                "credit": float(credit),
                "balance_debit": float(net) if net >= 0 else 0.0,
                "balance_credit": float(-net) if net < 0 else 0.0,
            }
        )
        total_debit += debit
        total_credit += credit
    return {
        "as_of_date": as_of_date.isoformat(),
        "rows": out,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "balanced": abs(total_debit - total_credit) < Decimal("0.01"),
    }


async def income_statement(
    session: AsyncSession, registry: _Registry, *, client_code: str | None, date_from: date, date_to: date,
) -> dict[str, Any]:
    """Revenue/Expense accounts only, over a date range — unlike trial
    balance and balance sheet, this is deliberately period-scoped (not
    cumulative-since-epoch) and never folds in opening balances, since a
    P&L is "what happened this period," not a running total."""
    from sqlalchemy import func

    gl_table = resolve_table(registry.get("gl_accounts"), registry)
    query = (
        select(
            gl_table.c.account_code,
            gl_table.c.account_name,
            gl_table.c.account_type,
            func.coalesce(func.sum(JournalLine.debit), 0).label("debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("credit"),
        )
        .select_from(gl_table)
        .join(JournalLine, JournalLine.account_code == gl_table.c.account_code)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            # See trial_balance()'s matching comment: a reversed entry and
            # its mirror must both count, or reversing anything silently
            # doubles the correction instead of netting to zero.
            JournalEntry.status.in_(("posted", "reversed")),
            JournalEntry.posting_date >= date_from,
            JournalEntry.posting_date <= date_to,
            gl_table.c.account_type.in_(["Revenue", "Expense"]),
        )
        .group_by(gl_table.c.account_code, gl_table.c.account_name, gl_table.c.account_type)
    )
    if client_code is not None:
        query = query.where(JournalEntry.client_code == client_code)
        # `gl_accounts` is one shared dynamic table across every tenant —
        # account_code is only unique *within* a client_code (ORG1 and ORG3
        # both legitimately have a "2200"). Joining on account_code alone
        # matches every tenant's row with that code, multiplying the summed
        # debit/credit by however many other orgs happen to reuse the same
        # code — this is what made the balance sheet not tie out even
        # though trial_balance() (which never joins gl_accounts at all) was
        # fine. Every other dynamic-table query in this codebase gets this
        # scoping for free via repository._scope(); this report bypasses
        # the repository entirely (raw JournalLine/JournalEntry join), so
        # it has to filter explicitly.
        if "client_code" in gl_table.c:
            query = query.where(gl_table.c.client_code == client_code)
    rows = (await session.execute(query)).all()

    revenue: list[dict[str, Any]] = []
    expenses: list[dict[str, Any]] = []
    total_revenue = Decimal("0")
    total_expenses = Decimal("0")
    for r in rows:
        debit, credit = _to_decimal(r.debit), _to_decimal(r.credit)
        if r.account_type == "Revenue":
            amount = credit - debit  # normal credit balance
            revenue.append({"account_code": r.account_code, "account_name": r.account_name, "amount": float(amount)})
            total_revenue += amount
        else:
            amount = debit - credit  # normal debit balance
            expenses.append({"account_code": r.account_code, "account_name": r.account_name, "amount": float(amount)})
            total_expenses += amount
    revenue.sort(key=lambda x: x["account_code"])
    expenses.sort(key=lambda x: x["account_code"])
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "revenue": revenue,
        "expenses": expenses,
        "total_revenue": float(total_revenue),
        "total_expenses": float(total_expenses),
        "net_income": float(total_revenue - total_expenses),
    }


async def balance_sheet(
    session: AsyncSession, registry: _Registry, *, client_code: str | None, as_of_date: date,
) -> dict[str, Any]:
    """Asset/Liability/Equity accounts, cumulative through `as_of_date`,
    plus opening balances for the fiscal year `as_of_date` falls in (same
    convention trial_balance() uses). The current fiscal year's net income
    (Revenue - Expense from Jan 1 of that year through `as_of_date`, via
    `income_statement()`) is folded into Equity as a synthetic "Current
    Year Earnings" line — without it a balance sheet pulled mid-year would
    never actually balance, since P&L accounts aren't themselves
    balance-sheet accounts until a year-end closing entry rolls them into
    retained earnings (which this system doesn't have a separate closing
    process for, so it's computed live instead)."""
    from sqlalchemy import func

    gl_table = resolve_table(registry.get("gl_accounts"), registry)
    query = (
        select(
            gl_table.c.account_code,
            gl_table.c.account_name,
            gl_table.c.account_type,
            func.coalesce(func.sum(JournalLine.debit), 0).label("debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("credit"),
        )
        .select_from(gl_table)
        .join(JournalLine, JournalLine.account_code == gl_table.c.account_code)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            # See trial_balance()'s matching comment: a reversed entry and
            # its mirror must both count, or reversing anything silently
            # doubles the correction instead of netting to zero.
            JournalEntry.status.in_(("posted", "reversed")),
            JournalEntry.posting_date <= as_of_date,
            gl_table.c.account_type.in_(["Asset", "Liability", "Equity"]),
        )
        .group_by(gl_table.c.account_code, gl_table.c.account_name, gl_table.c.account_type)
    )
    if client_code is not None:
        query = query.where(JournalEntry.client_code == client_code)
        # See the matching comment in income_statement() — gl_accounts is
        # shared across tenants, so the join must be scoped explicitly or
        # every other org reusing the same account_code gets summed in too.
        if "client_code" in gl_table.c:
            query = query.where(gl_table.c.client_code == client_code)
    rows = (await session.execute(query)).all()

    balances: dict[str, dict[str, Any]] = {
        r.account_code: {"account_code": r.account_code, "account_name": r.account_name, "account_type": r.account_type, "debit": _to_decimal(r.debit), "credit": _to_decimal(r.credit)}
        for r in rows
    }

    # Fold in opening balances the same way trial_balance() does — need
    # each opening-balance row's account_type from gl_accounts too, since
    # an account with an opening balance but zero journal activity won't
    # already be in `balances` from the query above.
    gl_type_lookup = select(gl_table.c.account_code, gl_table.c.account_name, gl_table.c.account_type)
    if client_code is not None and "client_code" in gl_table.c:
        gl_type_lookup = gl_type_lookup.where(gl_table.c.client_code == client_code)
    gl_type_by_code = {r.account_code: (r.account_name, r.account_type) for r in (await session.execute(gl_type_lookup)).all()}
    opening_table = resolve_table(registry.get("opening_balances"), registry)
    ob_query = select(opening_table).where(
        opening_table.c.deleted_at.is_(None), opening_table.c.scope == "GL_ACCOUNT", opening_table.c.fiscal_year == as_of_date.year,
    )
    if client_code is not None and "client_code" in opening_table.c:
        ob_query = ob_query.where(opening_table.c.client_code == client_code)
    for ob in (await session.execute(ob_query)).mappings().all():
        code = ob["gl_account_code"]
        if not code or code not in gl_type_by_code:
            continue
        name, acct_type = gl_type_by_code[code]
        if acct_type not in ("Asset", "Liability", "Equity"):
            continue
        amount = _to_decimal(ob["amount"])
        entry = balances.setdefault(code, {"account_code": code, "account_name": name, "account_type": acct_type, "debit": Decimal("0"), "credit": Decimal("0")})
        if amount >= 0:
            entry["debit"] += amount
        else:
            entry["credit"] += -amount

    assets, liabilities, equity = [], [], []
    total_assets = total_liabilities = total_equity = Decimal("0")
    for entry in sorted(balances.values(), key=lambda e: e["account_code"]):
        debit, credit = entry["debit"], entry["credit"]
        row = {"account_code": entry["account_code"], "account_name": entry["account_name"]}
        if entry["account_type"] == "Asset":
            amount = debit - credit
            row["amount"] = float(amount)
            assets.append(row)
            total_assets += amount
        elif entry["account_type"] == "Liability":
            amount = credit - debit
            row["amount"] = float(amount)
            liabilities.append(row)
            total_liabilities += amount
        else:  # Equity
            amount = credit - debit
            row["amount"] = float(amount)
            equity.append(row)
            total_equity += amount

    year_start = date(as_of_date.year, 1, 1)
    pl = await income_statement(session, registry, client_code=client_code, date_from=year_start, date_to=as_of_date)
    net_income = Decimal(str(pl["net_income"]))
    if net_income != 0:
        equity.append({"account_code": None, "account_name": "Current Year Earnings", "amount": float(net_income)})
        total_equity += net_income

    return {
        "as_of_date": as_of_date.isoformat(),
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "total_equity": float(total_equity),
        "total_liabilities_and_equity": float(total_liabilities + total_equity),
        "balanced": abs(total_assets - (total_liabilities + total_equity)) < Decimal("0.01"),
    }


async def subledger_reconciliation(
    session: AsyncSession, registry: _Registry, *, client_code: str | None, as_of_date: date,
) -> dict[str, Any]:
    """For every GL account flagged `gl_accounts.is_reconciliation_account`,
    compares its trial-balance balance against the total obtained by
    replaying every posting_rules header line that could resolve to it —
    across every currently-posted record of every module — using the exact
    same resolver `posting.py` uses at post time (`_resolve_rule_account`),
    so this can never drift from what posting actually does. Generic over
    module metadata rather than a hardcoded module list: a new module wired
    into `gl_account_determination`/`subledger` automatically participates.

    A nonzero variance means either (a) a posted record's amount/party
    fields were altered after posting (only possible by bypassing the
    workflow-lock enforcement, e.g. a direct DB edit — the lock itself
    blocks this through the API), or (b) something posts to a reconciliation
    account through a path this report doesn't yet replay. Either way the
    variance is the signal, not a silent mismatch buried in two separate
    reports."""
    import metaforge_api.infrastructure.posting as posting
    from metaforge_api.domain.formulas import evaluate_formula

    gl_table = resolve_table(registry.get("gl_accounts"), registry)
    recon_rows = (
        await session.execute(
            select(gl_table.c.account_code, gl_table.c.account_name).where(gl_table.c.is_reconciliation_account.is_(True))
        )
    ).all()
    recon_codes = {r.account_code for r in recon_rows}
    if not recon_codes:
        return {"as_of_date": as_of_date.isoformat(), "accounts": []}

    tb = await trial_balance(session, registry, client_code=client_code, as_of_date=as_of_date)
    tb_by_code = {r["account_code"]: r for r in tb["rows"]}

    subledger: dict[str, dict[str, Any]] = {code: {"debit": Decimal("0"), "credit": Decimal("0"), "sources": {}} for code in recon_codes}

    for module in registry.all().values():
        rules = module.posting_rules
        if not rules:
            continue
        lines = [l for l in rules.get("lines", []) if l.get("type", "header") == "header"]
        if not lines:
            continue
        status_field = (module.workflow or {}).get("field")
        trigger_status = rules.get("trigger_status")
        table = resolve_table(module, registry)
        if not status_field or not trigger_status or status_field not in table.c:
            continue
        date_field = rules.get("date_field")
        if not date_field or date_field not in table.c:
            continue

        query = select(table).where(
            table.c.deleted_at.is_(None),
            table.c[status_field] == trigger_status,
            table.c[date_field] <= as_of_date,
        )
        if client_code is not None and "client_code" in table.c:
            query = query.where(table.c.client_code == client_code)
        records = (await session.execute(query)).mappings().all()

        for line in lines:
            try:
                account_code, _ = await posting._resolve_rule_account(session, registry, client_code, module, line, {})
            except posting.PostingError:
                account_code = None
            # Literal/determination-only lines resolve identically for every
            # record; only a `subledger` line can vary per record, so only
            # bother re-resolving per-record when the rule actually has one.
            varies_per_record = bool(line.get("subledger"))
            if not varies_per_record and account_code not in recon_codes:
                continue
            for record in records:
                try:
                    if varies_per_record:
                        account_code, _ = await posting._resolve_rule_account(session, registry, client_code, module, line, dict(record))
                    if account_code not in recon_codes:
                        continue
                    amount = Decimal(str(evaluate_formula(line["amount_formula"], dict(record))))
                except Exception:
                    continue
                if amount == 0:
                    continue
                bucket = subledger[account_code]
                if line["side"] == "debit":
                    bucket["debit"] += amount
                else:
                    bucket["credit"] += amount
                bucket["sources"][module.name] = bucket["sources"].get(module.name, 0) + 1

    accounts = []
    for code, name in sorted(recon_rows):
        gl_row = tb_by_code.get(code)
        gl_debit = Decimal(str(gl_row["debit"])) if gl_row else Decimal("0")
        gl_credit = Decimal(str(gl_row["credit"])) if gl_row else Decimal("0")
        gl_net = gl_debit - gl_credit
        sub = subledger[code]
        sub_net = sub["debit"] - sub["credit"]
        variance = gl_net - sub_net
        accounts.append(
            {
                "account_code": code,
                "account_name": name,
                "gl_balance": float(gl_net),
                "subledger_balance": float(sub_net),
                "variance": float(variance),
                "matched": abs(variance) < Decimal("0.01"),
                "sources": sub["sources"],
            }
        )
    return {
        "as_of_date": as_of_date.isoformat(),
        "accounts": accounts,
        "all_matched": all(a["matched"] for a in accounts),
    }


def _bucket_for(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "current"
    if days_overdue <= 30:
        return "1-30"
    if days_overdue <= 60:
        return "31-60"
    if days_overdue <= 90:
        return "61-90"
    return "90+"


async def aging_report(
    session: AsyncSession, registry: _Registry, *, client_code: str | None, group: str, as_of_date: date,
) -> list[dict[str, Any]]:
    modules = [m for m in _group_modules(registry, group) if m.clearing_config.get("sign", "positive") == "positive"]
    if not modules:
        raise ReportError(f"no invoice-side clearing-enabled module found for group '{group}'")

    out: list[dict[str, Any]] = []
    for module in modules:
        cfg = module.clearing_config
        has_due_date = any(f.name == "due_date" for f in module.fields)
        label_field = _label_field(module)
        party_module = cfg.get("party_module")
        rows = await clearing.list_open_items(session, registry, module.name, client_code=client_code, limit=500)
        for row in rows:
            due = row.get("due_date") if has_due_date else None
            days_overdue = (as_of_date - due).days if due else 0
            party_id = row.get(cfg.get("party_field")) if cfg.get("party_field") else None
            out.append(
                {
                    "module": module.name,
                    "record_id": str(row["id"]),
                    "document_label": str(row[label_field]) if label_field and row.get(label_field) else module.label,
                    "party_module": party_module,
                    "party_id": str(party_id) if party_id else None,
                    "due_date": due.isoformat() if due else None,
                    "days_overdue": max(days_overdue, 0),
                    "bucket": _bucket_for(days_overdue) if due else "current",
                    "amount": float(_to_decimal(row.get(cfg["amount_field"]))),
                }
            )

    party_ids = {row["party_id"] for row in out if row["party_id"]}
    labels: dict[str, str] = {}
    if party_ids and modules[0].clearing_config.get("party_module"):
        party_module = modules[0].clearing_config["party_module"]
        for pid in party_ids:
            labels[pid] = await _resolve_party_label(session, registry, party_module, uuid.UUID(pid))
    for row in out:
        row["party_label"] = labels.get(row["party_id"]) if row["party_id"] else None

    out.sort(key=lambda r: (-r["days_overdue"], r["document_label"]))
    return out


async def party_ledger(
    session: AsyncSession, registry: _Registry, *, client_code: str | None, group: str, party_id: uuid.UUID, date_from: date, date_to: date,
) -> dict[str, Any]:
    modules = _group_modules(registry, group)
    if not modules:
        raise ReportError(f"no clearing-enabled modules found for group '{group}'")

    party_field = modules[0].clearing_config["party_field"]
    party_module = modules[0].clearing_config.get("party_module")
    fiscal_year_start = date(date_from.year, 1, 1)

    opening = Decimal("0")
    scope = _GROUP_TO_PARTY_SCOPE.get(group)
    if scope:
        opening_module = registry.get("opening_balances")
        opening_table = resolve_table(opening_module, registry)
        ob_field = "vendor_id" if scope == "VENDOR" else "customer_id"
        ob_query = select(opening_table).where(
            opening_table.c.deleted_at.is_(None),
            opening_table.c.scope == scope,
            opening_table.c.fiscal_year == date_from.year,
            opening_table.c[ob_field] == party_id,
        )
        if client_code is not None and "client_code" in opening_table.c:
            ob_query = ob_query.where(opening_table.c.client_code == client_code)
        ob_row = (await session.execute(ob_query)).mappings().first()
        if ob_row:
            opening += _to_decimal(ob_row["amount"])

    raw_entries: list[dict[str, Any]] = []
    for module in modules:
        cfg = module.clearing_config
        table = resolve_table(module, registry)
        date_field = _date_field(module)
        if date_field is None or party_field not in table.c:
            continue
        label_field = _label_field(module)
        sign = 1 if cfg.get("sign", "positive") == "positive" else -1

        query = select(table).where(table.c.deleted_at.is_(None), table.c[party_field] == party_id, table.c[date_field] >= fiscal_year_start, table.c[date_field] <= date_to)
        if client_code is not None and "client_code" in table.c:
            query = query.where(table.c.client_code == client_code)
        posted_filter = clearing._posted_only_filter(module, table)
        if posted_filter is not None:
            query = query.where(posted_filter)
        rows = (await session.execute(query)).mappings().all()
        for row in rows:
            d = row[date_field]
            d = d.date() if hasattr(d, "date") and not isinstance(d, date) else d
            amount = _to_decimal(row.get(cfg["amount_field"])) * sign
            if d < date_from:
                opening += amount
            else:
                raw_entries.append(
                    {
                        "module": module.name,
                        "record_id": str(row["id"]),
                        "date": d.isoformat(),
                        "_date": d,
                        "document_label": str(row[label_field]) if label_field and row.get(label_field) else module.label,
                        "amount": float(amount),
                    }
                )

    raw_entries.sort(key=lambda e: (e["_date"], e["document_label"]))
    running = opening
    entries = []
    for e in raw_entries:
        running += Decimal(str(e["amount"]))
        entries.append({k: v for k, v in e.items() if k != "_date"} | {"balance": float(running)})

    party_label = await _resolve_party_label(session, registry, party_module, party_id) if party_module else None
    return {
        "party_id": str(party_id),
        "party_label": party_label,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "opening_balance": float(opening),
        "entries": entries,
        "closing_balance": float(running),
    }
