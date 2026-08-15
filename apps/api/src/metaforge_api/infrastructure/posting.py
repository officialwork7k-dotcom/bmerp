"""Posting engine core: turns a document transitioning into its
`posting_rules.trigger_status` into an immutable journal_entry + its
journal_lines.

Deliberately NOT a Builder module, unlike almost everything else in this
framework: a journal entry has invariants metadata can't express —
double-entry balance validation (sum(debit) == sum(credit)), immutability
once posted (nothing here ever UPDATEs a journal_lines row; a correction is
a reversal, a new entry), and point-in-time account snapshotting (account
code/name are copied onto the line at post time rather than looked up live,
so a later rename of the account doesn't rewrite history). Those are
algorithmic, not declarative — this is the "engine service" tier: generic,
written once, configured per-module via ModuleMetadata.posting_rules, not
per-module code.

GL account resolution (added for the MM/SD-FI/CO account-determination
integration): a posting_rules header-line rule no longer has to hardcode
`account_code`/`account_name` — it can instead say `"determination_key":
"INVENTORY"` (resolved against the `gl_account_determination` Builder
module, one admin-editable row per abstract transaction key, optionally
scoped by client_code) or `"subledger": {...}` (resolved against a party
record — e.g. a vendor's `category_id` → its `vendor_categories` row's
`ap_gl_account_id` — falling back to a `determination_key` default when the
party has no category override). This mirrors SAP OBYC's transaction-key
account determination plus the "alternative reconciliation account"
override on vendor/customer/asset master data. Resolution always happens at
*post* time and is baked into the snapshotted journal_lines row — never
re-resolved later, so an admin changing a determination row never rewrites
already-posted history (corrections go through `reverse()` + repost, same
as any other change).

Idempotent per document: re-triggering the same posting transition (a
retried request, a workflow that allows re-entering the same state) is a
no-op if a non-reversed journal_entry already exists for that document —
callers never end up with two journal entries for one document.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.formulas import evaluate_formula
from metaforge_api.domain.metadata import ModuleMetadata
from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import JournalEntry, JournalLine

_ROUNDING_TOLERANCE = Decimal("0.05")


class PostingError(Exception):
    pass


class _Registry(Protocol):
    def get(self, name: str) -> ModuleMetadata: ...


@dataclass
class _LineDraft:
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _to_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


async def _gl_account_by_id(session: AsyncSession, registry: _Registry, gl_account_id: Any) -> tuple[str, str]:
    gl_table = resolve_table(registry.get("gl_accounts"), registry)
    row = (
        await session.execute(
            select(gl_table.c.account_code, gl_table.c.account_name).where(gl_table.c.id == _to_uuid(gl_account_id))
        )
    ).first()
    if row is None:
        raise PostingError(f"configured GL account {gl_account_id} not found in gl_accounts")
    return row.account_code, row.account_name


async def _gl_account_by_code(session: AsyncSession, registry: _Registry, code: str) -> tuple[str, str]:
    gl_table = resolve_table(registry.get("gl_accounts"), registry)
    row = (
        await session.execute(select(gl_table.c.account_code, gl_table.c.account_name).where(gl_table.c.account_code == code))
    ).first()
    if row is None:
        # A free-text account code (e.g. bank_accounts.gl_account_code) with
        # no matching gl_accounts master row — tolerate it rather than
        # blocking the posting, using the code itself as the label. Real
        # misconfiguration here shows up immediately in the trial balance
        # as an orphan account code with no master-data name.
        return str(code), str(code)
    return row.account_code, row.account_name


async def _resolve_determination_account(
    session: AsyncSession, registry: _Registry, client_code: str | None, determination_key: str
) -> tuple[str, str]:
    """Every dynamic table (including `gl_account_determination` itself)
    carries a system-managed, NOT NULL `client_code` column — the framework
    already scopes each client to its own rows, so "one row per
    (client_code, determination_key)" is the natural shape here; there's no
    separate global-fallback row to fall further back to beyond this."""
    det_table = resolve_table(registry.get("gl_account_determination"), registry)
    query = select(det_table.c.gl_account_id).where(
        det_table.c.determination_key == determination_key, det_table.c.deleted_at.is_(None)
    )
    if client_code is not None and "client_code" in det_table.c:
        query = query.where(det_table.c.client_code == client_code)
    row = (await session.execute(query)).first()
    if row is None or not row.gl_account_id:
        raise PostingError(
            f"no GL Account Determination configured for key '{determination_key}' "
            f"(client '{client_code}') — add a row for it in the GL Account Determination module"
        )
    return await _gl_account_by_id(session, registry, row.gl_account_id)


async def _resolve_subledger_account(
    session: AsyncSession,
    registry: _Registry,
    client_code: str | None,
    module: ModuleMetadata,
    record: dict[str, Any],
    cfg: dict[str, Any],
    fallback_key: str | None,
) -> tuple[str, str]:
    """`cfg`: `{"party_field": "vendor_id", "account_field": ..., "category_field": ...?, "category_module": ...?}`.
    Category mode (category_field set): party → party.category_id → category row's account_field
    (a LOOKUP to gl_accounts). Direct mode (no category_field): party.account_field is read straight
    off the party row (e.g. bank_accounts.gl_account_code, a plain TEXT account code). Either mode
    falls back to the global `fallback_key` determination row when the party has no override —
    never silently posts to nothing."""
    party_field_name = cfg["party_field"]
    party_id = record.get(party_field_name)
    if not party_id:
        if fallback_key:
            return await _resolve_determination_account(session, registry, client_code, fallback_key)
        raise PostingError(f"subledger party field '{party_field_name}' is empty and no fallback determination_key is configured")

    party_field_meta = module.field(party_field_name)
    if party_field_meta is None or not party_field_meta.lookup_module:
        raise PostingError(f"subledger party_field '{party_field_name}' is not a LOOKUP field on module '{module.name}'")
    party_table = resolve_table(registry.get(party_field_meta.lookup_module), registry)
    party_row = (await session.execute(select(party_table).where(party_table.c.id == _to_uuid(party_id)))).mappings().first()
    if party_row is None:
        raise PostingError(f"subledger party record not found: {party_field_meta.lookup_module}/{party_id}")

    account_field = cfg["account_field"]
    category_field = cfg.get("category_field")

    if category_field:
        category_id = party_row.get(category_field)
        if category_id:
            category_table = resolve_table(registry.get(cfg["category_module"]), registry)
            category_row = (
                await session.execute(select(category_table).where(category_table.c.id == _to_uuid(category_id)))
            ).mappings().first()
            gl_account_id = category_row.get(account_field) if category_row else None
            if gl_account_id:
                return await _gl_account_by_id(session, registry, gl_account_id)
        if fallback_key:
            return await _resolve_determination_account(session, registry, client_code, fallback_key)
        raise PostingError(
            f"party {party_field_meta.lookup_module}/{party_id} has no category override for "
            f"'{account_field}' and no fallback determination_key is configured"
        )

    direct_value = party_row.get(account_field)
    if direct_value:
        return await _gl_account_by_code(session, registry, str(direct_value))
    if fallback_key:
        return await _resolve_determination_account(session, registry, client_code, fallback_key)
    raise PostingError(
        f"party {party_field_meta.lookup_module}/{party_id} has no '{account_field}' set and "
        "no fallback determination_key is configured"
    )


async def _resolve_rule_account(
    session: AsyncSession, registry: _Registry, client_code: str | None, module: ModuleMetadata, rule: dict, record: dict[str, Any]
) -> tuple[str, str]:
    """Literal `account_code` always wins (full backward compatibility with
    every posting_rules line written before this resolver existed). Otherwise
    `subledger` (party/category-based) or `determination_key` (flat,
    admin-configurable) — exactly one is expected per rule."""
    if rule.get("account_code"):
        return rule["account_code"], rule.get("account_name", rule["account_code"])
    if rule.get("subledger"):
        return await _resolve_subledger_account(session, registry, client_code, module, record, rule["subledger"], rule.get("determination_key"))
    if rule.get("determination_key"):
        return await _resolve_determination_account(session, registry, client_code, rule["determination_key"])
    raise PostingError("posting rule line has none of account_code, subledger, or determination_key")


async def _reject_if_reconciliation_account(
    session: AsyncSession, registry: _Registry, client_code: str | None, account_code: str
) -> None:
    """Reconciliation accounts (AP/AR/asset control accounts — anything
    `gl_accounts.is_reconciliation_account` flags) update *only* through
    the automatic subledger mechanism (`determination_key`/`subledger` on a
    module's posting_rules); a free-typed manual journal line (the only
    posting path where a human picks an account_code directly, not one
    resolved by the engine) must never be allowed to post straight to one
    — that's exactly the drift that breaks a reconciliation account's
    balance matching its subledger total.

    `gl_accounts` is one shared dynamic table across every tenant, and
    account_code is only unique *within* a client_code — without this
    filter, `.first()` on a bare account_code match returns whichever
    tenant's row the query happens to see first, so a manual journal could
    be wrongly blocked (another org's same-numbered account happens to be
    flagged reconciliation) or, worse, wrongly *allowed* through to an
    actual reconciliation account (the match landed on a different org's
    non-flagged row instead of this org's flagged one)."""
    gl_table = resolve_table(registry.get("gl_accounts"), registry)
    query = select(gl_table.c.is_reconciliation_account).where(gl_table.c.account_code == account_code)
    if client_code is not None and "client_code" in gl_table.c:
        query = query.where(gl_table.c.client_code == client_code)
    row = (await session.execute(query)).first()
    if row is not None and row.is_reconciliation_account:
        raise PostingError(
            f"account '{account_code}' is a reconciliation account — it updates automatically from subledger "
            "transactions (vendor/customer invoices, payments, asset postings) and cannot be posted to directly "
            "via a manual journal entry"
        )


async def _per_child_lines(
    session: AsyncSession, rule: dict, module: ModuleMetadata, record: dict[str, Any], registry: _Registry, client_code: str | None
) -> list[_LineDraft]:
    rel = next((r for r in module.embedded_children() if r.name == rule["child_relation"]), None)
    if rel is None:
        raise PostingError(f"posting rule references unknown embedded relationship '{rule['child_relation']}'")
    child_module = registry.get(rel.related_module)
    child_table = resolve_table(child_module, registry)
    rows = (
        await session.execute(
            select(child_table).where(
                child_table.c[rel.foreign_key] == record["id"], child_table.c.deleted_at.is_(None)
            )
        )
    ).mappings().all()

    account_field = rule["account_field"]
    name_field = rule.get("account_name_field")
    # Optional: a LOOKUP field on the child row pointing at gl_accounts — a
    # manual journal line picked from the real chart of accounts instead of
    # a free-typed code, so a typo can't post an orphan account that only
    # ever shows up as a nameless code in the trial balance. When set (and
    # the row actually has a value in it), it wins outright: the account is
    # dereferenced and its own account_code/account_name are snapshotted,
    # exactly like every other account-resolution path in this module —
    # `account_field`/`account_name_field` become a pure display fallback
    # for older rows that predate the LOOKUP column.
    account_lookup_field = rule.get("account_lookup_field")
    gl_table = resolve_table(registry.get("gl_accounts"), registry) if account_lookup_field else None
    debit_field = rule["debit_field"]
    credit_field = rule["credit_field"]
    lines: list[_LineDraft] = []
    for row in rows:
        debit = _to_decimal(row.get(debit_field))
        credit = _to_decimal(row.get(credit_field))
        if debit == 0 and credit == 0:
            continue
        account_code: Any = None
        account_name: Any = None
        lookup_id = row.get(account_lookup_field) if account_lookup_field else None
        if lookup_id is not None and gl_table is not None:
            account_code, account_name = await _gl_account_by_id(session, registry, lookup_id)
        else:
            account_code = row.get(account_field)
            if not account_code:
                continue
            account_name = row.get(name_field) if name_field else account_code
        if rule.get("block_reconciliation_accounts", True):
            await _reject_if_reconciliation_account(session, registry, client_code, str(account_code))
        lines.append(_LineDraft(str(account_code), str(account_name), debit, credit))
    return lines


async def _per_child_grouped_lines(
    session: AsyncSession, registry: _Registry, client_code: str | None, rule: dict, module: ModuleMetadata, record: dict[str, Any]
) -> list[_LineDraft]:
    """Splits one header amount across N journal lines, one per distinct
    value of `group_field` on the child rows' looked-up item — e.g. a GR's
    inventory value split by material group (raw material vs. finished
    good) instead of one flat INVENTORY line for the whole receipt,
    mirroring SAP OBYC's per-valuation-class account determination.
    `amount_field` names a field already stored on the child row (e.g.
    `line_value`); `determination_key_template` is formatted with `{group}`
    (Python str.format) to look up a per-group override row, falling back
    to the plain `fallback_key` when no override exists yet or the item has
    no group set — so this degrades gracefully to today's flat-account
    behavior until an admin actually seeds the per-group determination
    rows, rather than failing closed."""
    rel = next((r for r in module.embedded_children() if r.name == rule["child_relation"]), None)
    if rel is None:
        raise PostingError(f"posting rule references unknown embedded relationship '{rule['child_relation']}'")
    child_module = registry.get(rel.related_module)
    child_table = resolve_table(child_module, registry)
    rows = (
        await session.execute(
            select(child_table).where(
                child_table.c[rel.foreign_key] == record["id"], child_table.c.deleted_at.is_(None)
            )
        )
    ).mappings().all()

    item_table = resolve_table(registry.get(rule["item_module"]), registry)
    item_field = rule["item_field"]
    group_field = rule["group_field"]
    amount_field = rule["amount_field"]

    totals: dict[str | None, Decimal] = {}
    for row in rows:
        amount = _to_decimal(row.get(amount_field))
        if amount == 0:
            continue
        item_id = row.get(item_field)
        group = None
        if item_id:
            item_row = (
                await session.execute(select(item_table.c[group_field]).where(item_table.c.id == item_id))
            ).first()
            group = item_row[0] if item_row else None
        totals[group] = totals.get(group, Decimal("0")) + amount

    side = rule["side"]
    if side not in ("debit", "credit"):
        raise PostingError(f"per_child_grouped posting rule side must be 'debit' or 'credit', got {side!r}")
    lines: list[_LineDraft] = []
    for group, amount in totals.items():
        if amount == 0:
            continue
        key = rule["determination_key_template"].format(group=group) if group else rule["fallback_key"]
        try:
            account_code, account_name = await _resolve_determination_account(session, registry, client_code, key)
        except PostingError:
            account_code, account_name = await _resolve_determination_account(session, registry, client_code, rule["fallback_key"])
        debit = amount if side == "debit" else Decimal("0")
        credit = amount if side == "credit" else Decimal("0")
        lines.append(_LineDraft(account_code, account_name, debit, credit))
    return lines


async def _synthetic_grouped_lines(
    session: AsyncSession, registry: _Registry, client_code: str | None, rule: dict, record: dict[str, Any]
) -> list[_LineDraft]:
    """Same per-group account split as `per_child_grouped`, but reads its
    `{group: amount}` totals from a dict already computed onto `record` by
    the caller (`source_field`) instead of querying embedded child rows
    itself. Exists for cases where the grouped amount isn't a plain stored
    field on a child row at all — a Delivery's COGS is the stock ledger's
    moving-average cost *at the moment of the stock-out*, which only exists
    after `stock.apply_stock_rules` has actually run; repository.transition()
    computes `_stock_issue_cost_by_group` from those results the same way
    it already computes the flat `_stock_issue_cost_total`, and this rule
    type just spends it. Same graceful-degradation contract as
    per_child_grouped: an unrecognized/absent group falls back to
    `fallback_key`, so this only ever *adds* precision once an admin seeds
    per-group determination rows — it never fails closed."""
    totals: dict[str, Decimal] = record.get(rule["source_field"]) or {}
    side = rule["side"]
    if side not in ("debit", "credit"):
        raise PostingError(f"synthetic_grouped posting rule side must be 'debit' or 'credit', got {side!r}")
    lines: list[_LineDraft] = []
    for group, amount in totals.items():
        if not amount:
            continue
        key = rule["determination_key_template"].format(group=group) if group else rule["fallback_key"]
        try:
            account_code, account_name = await _resolve_determination_account(session, registry, client_code, key)
        except PostingError:
            account_code, account_name = await _resolve_determination_account(session, registry, client_code, rule["fallback_key"])
        debit = amount if side == "debit" else Decimal("0")
        credit = amount if side == "credit" else Decimal("0")
        lines.append(_LineDraft(account_code, account_name, debit, credit))
    return lines


def _header_line(rule: dict, record: dict[str, Any]) -> _LineDraft:
    amount = Decimal(str(evaluate_formula(rule["amount_formula"], record)))
    if amount < 0:
        raise PostingError(f"header posting rule for account '{rule['account_code']}' produced a negative amount")
    side = rule["side"]
    if side not in ("debit", "credit"):
        raise PostingError(f"header posting rule side must be 'debit' or 'credit', got {side!r}")
    debit = amount if side == "debit" else Decimal("0")
    credit = amount if side == "credit" else Decimal("0")
    return _LineDraft(rule["account_code"], rule.get("account_name", rule["account_code"]), debit, credit)


def _resolve_posting_date(rules: dict, record: dict[str, Any]) -> date:
    date_field = rules.get("date_field")
    value = record.get(date_field) if date_field else None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value[:10])
    return datetime.now(timezone.utc).date()


async def post_document(
    session: AsyncSession,
    module: ModuleMetadata,
    record: dict[str, Any],
    registry: _Registry,
    *,
    client_code: str | None,
    actor_id: uuid.UUID | None,
    rules: dict | None = None,
    document_module: str | None = None,
) -> JournalEntry | None:
    """No-op (returns None) if the module has no posting_rules, OR if every
    configured line evaluates to a zero amount (e.g. a service-only Delivery
    has nothing to post to COGS/Inventory — that's a legitimate no-op, not a
    misconfiguration, and must never block the workflow transition that
    triggered it). Raises PostingError if the *rules themselves* produce no
    lines at all, or a nonzero-but-unbalanced entry — the caller's
    transaction rolls back, so a document can never move into its
    trigger_status with a broken posting.

    `rules`/`document_module` let a caller post a *second* lifecycle event
    for the same record under a different ruleset — e.g. a fixed asset's
    disposal, distinct from its acquisition — without the two colliding.
    Default (both None, the overwhelming common case) behaves exactly as
    before: reads `module.posting_rules` and keys the idempotency check on
    plain `module.name`, so every existing single-trigger module is
    unaffected. A caller posting an *additional* trigger passes its own
    rules dict plus a distinct `document_module` (e.g.
    `"fixed_assets:disposed"`) so this event gets its own idempotency slot
    instead of being shadowed by (or shadowing) the acquisition posting
    already on file for the same document_id."""
    rules = rules if rules is not None else module.posting_rules
    if not rules:
        return None
    doc_module_key = document_module or module.name

    existing = (
        await session.execute(
            select(JournalEntry).where(
                JournalEntry.document_module == doc_module_key,
                JournalEntry.document_id == record["id"],
                JournalEntry.status == "posted",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    rule_defs = rules.get("lines", [])
    if not rule_defs:
        raise PostingError(f"posting_rules for '{module.name}' has no lines configured")

    lines: list[_LineDraft] = []
    for rule in rule_defs:
        rule_type = rule.get("type")
        if rule_type == "per_child":
            lines.extend(await _per_child_lines(session, rule, module, record, registry, client_code))
        elif rule_type == "per_child_grouped":
            lines.extend(await _per_child_grouped_lines(session, registry, client_code, rule, module, record))
        elif rule_type == "synthetic_grouped":
            lines.extend(await _synthetic_grouped_lines(session, registry, client_code, rule, record))
        elif rule_type == "header":
            account_code, account_name = await _resolve_rule_account(session, registry, client_code, module, rule, record)
            resolved_rule = {**rule, "account_code": account_code, "account_name": account_name}
            line = _header_line(resolved_rule, record)
            if line.debit != 0 or line.credit != 0:
                lines.append(line)
        else:
            raise PostingError(f"unknown posting line rule type: {rule_type!r}")

    if not lines:
        # Every rule evaluated to zero — a legitimate no-op (e.g. a
        # service-only delivery with nothing to post to COGS), not an error.
        return None

    total_debit = sum((line.debit for line in lines), Decimal("0"))
    total_credit = sum((line.credit for line in lines), Decimal("0"))
    diff = total_debit - total_credit
    if diff != 0 and abs(diff) <= _ROUNDING_TOLERANCE:
        # Tax/percentage rounding can leave a document off by a cent or two
        # — post the difference to a dedicated rounding account rather than
        # hard-failing on what is, functionally, not a real imbalance.
        code, name = await _resolve_determination_account(session, registry, client_code, "ROUNDING_DIFF")
        if diff > 0:
            lines.append(_LineDraft(code, name, Decimal("0"), diff))
        else:
            lines.append(_LineDraft(code, name, -diff, Decimal("0")))
        total_debit = sum((line.debit for line in lines), Decimal("0"))
        total_credit = sum((line.credit for line in lines), Decimal("0"))

    if total_debit != total_credit:
        raise PostingError(
            f"journal entry for {module.name}/{record['id']} is not balanced: "
            f"debit {total_debit} != credit {total_credit}"
        )

    entry = JournalEntry(
        client_code=client_code,
        document_module=doc_module_key,
        document_id=record["id"],
        posting_date=_resolve_posting_date(rules, record),
        description=f"{module.label} {record['id']}",
        status="posted",
        posted_by=actor_id,
        posted_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.flush()  # assigns entry.id, needed by the lines below
    for line_no, line in enumerate(lines, start=1):
        session.add(
            JournalLine(
                journal_entry_id=entry.id,
                line_no=line_no,
                account_code=line.account_code,
                account_name=line.account_name,
                debit=line.debit,
                credit=line.credit,
            )
        )
    return entry


async def reverse(session: AsyncSession, journal_entry_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> JournalEntry:
    """Corrections never edit a posted entry — they reverse it (a mirrored
    entry with every line's debit/credit swapped) and mark the original
    `reversed`. Both are append-only writes; nothing here mutates an
    existing journal_lines row. A reversal always mirrors the *snapshotted*
    account_code/account_name already on the original lines — it never
    re-resolves accounts, so a GL Account Determination change made after
    the original posting never leaks into a reversal of it."""
    original = (await session.execute(select(JournalEntry).where(JournalEntry.id == journal_entry_id))).scalar_one_or_none()
    if original is None:
        raise LookupError(f"journal entry not found: {journal_entry_id}")
    if original.status != "posted":
        raise PostingError(f"only a posted entry can be reversed (status is '{original.status}')")
    lines = (await session.execute(select(JournalLine).where(JournalLine.journal_entry_id == original.id))).scalars().all()

    reversal = JournalEntry(
        client_code=original.client_code,
        document_module=original.document_module,
        document_id=original.document_id,
        posting_date=datetime.now(timezone.utc).date(),
        description=f"Reversal of {original.description}",
        status="posted",
        reversal_of=original.id,
        posted_by=actor_id,
        posted_at=datetime.now(timezone.utc),
    )
    session.add(reversal)
    await session.flush()
    for line_no, line in enumerate(lines, start=1):
        session.add(
            JournalLine(
                journal_entry_id=reversal.id,
                line_no=line_no,
                account_code=line.account_code,
                account_name=line.account_name,
                debit=line.credit,
                credit=line.debit,
            )
        )
    original.status = "reversed"
    return reversal


async def backfill_missing_postings(
    session: AsyncSession, registry: _Registry, module_name: str, *, client_code: str | None, actor_id: uuid.UUID | None
) -> list[JournalEntry]:
    """GL hygiene tool: finds every record already sitting in its module's
    posting `trigger_status` with no journal entry to show for it (the
    known failure mode being a document posted *before* posting_rules
    existed on that module, or before this module had a valid rule) and
    posts it now. Idempotent and safe to run repeatedly — only ever creates
    an entry where one is genuinely missing."""
    module = registry.get(module_name)
    if not module.posting_rules or not module.workflow:
        return []
    status_field = module.workflow["field"]
    trigger_status = module.posting_rules.get("trigger_status")
    if not trigger_status:
        return []

    table = resolve_table(module, registry)
    query = select(table).where(table.c.deleted_at.is_(None), table.c[status_field] == trigger_status)
    if client_code is not None and "client_code" in table.c:
        query = query.where(table.c.client_code == client_code)
    rows = (await session.execute(query)).mappings().all()

    created: list[JournalEntry] = []
    for row in rows:
        already = (
            await session.execute(
                select(JournalEntry.id).where(
                    JournalEntry.document_module == module_name,
                    JournalEntry.document_id == row["id"],
                    JournalEntry.status == "posted",
                )
            )
        ).scalar_one_or_none()
        if already is not None:
            continue
        entry = await post_document(
            session, module, dict(row), registry,
            client_code=row.get("client_code", client_code), actor_id=actor_id,
        )
        if entry is not None:
            created.append(entry)
    return created
