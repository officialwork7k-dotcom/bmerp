"""Generic tool layer between the LLM chat loop and the existing
DataRepository — the whole point of this module is that it adds ZERO new
business logic. Every read/write goes through the exact same repository
methods the regular web UI uses, so tenant scoping, workflow locks,
create_guards, SoD, and posting/stock/clearing rules all apply exactly as
they already do. This module only adds what a raw repository call is
missing when the caller is an LLM instead of an authenticated HTTP route:

- module_permissions re-check (DataRepository has none of its own — see
  api/deps.py's `require_permission`; a router enforces it per-request via
  a path param, but one chat request can touch many modules per turn, so
  this layer re-implements the same check per tool call).
- provenance enforcement: a LOOKUP value or a transition target's id must
  have come from a search_records/resolve_lookup/get_record/list_records/
  create_record call earlier in THIS SAME chat turn. This is the one
  concrete guardrail against both hallucinated ids and a stored-prompt-
  injection payload (e.g. a vendor name containing text that reads like an
  instruction) ever reaching a write — the LLM can act on what it just
  looked up, never on an id it merely asserts.
- a write allowlist + per-action amount cap (infrastructure.models.AiSettings),
  so "auto-post when confident" still has a server-side (not just
  prompted) ceiling on the single riskiest action this feature can take.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.metadata import FieldDataType, ModuleMetadata
from metaforge_api.infrastructure import financial_reports, reports as adhoc_reports
from metaforge_api.infrastructure.approval_rules import ApprovalRequiredError
from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import AiConversation, AiConversationMessage, AiSettings
from metaforge_api.infrastructure.module_registry import SessionModuleRegistry
from metaforge_api.infrastructure.repository import (
    ChildDiff,
    ConcurrencyConflict,
    CreateGuardBlocked,
    DataRepository,
    LookupScopeError,
)

_SEARCHABLE_TYPES = {
    FieldDataType.TEXT, FieldDataType.LONG_TEXT, FieldDataType.EMAIL,
    FieldDataType.ENUM, FieldDataType.PHONE, FieldDataType.URL,
}
_SEARCH_LIMIT = 8
_LIST_LIMIT = 20


class ToolError(Exception):
    """Any rejection the LLM should see as a tool result, not a crash —
    wrong permission, unresolved provenance, disallowed module, etc."""


class ToolContext:
    def __init__(self, *, session: AsyncSession, registry: SessionModuleRegistry, user, repo: DataRepository, ai_settings: AiSettings | None):
        self.session = session
        self.registry = registry
        self.user = user
        self.repo = repo
        self.ai_settings = ai_settings
        # The current turn's scanned document's own grand_total (Decimal),
        # if this turn attached an image and extraction produced one — see
        # chat_service.run_chat_turn. None for a typed-only turn, or when
        # the document had no readable total. _create_record uses this as a
        # ceiling: a document created from a scan may never be recorded for
        # MORE than the document itself says is owed (see the invoice
        # #470831 incident this guards against — a header-level discount
        # that had nowhere to be recorded produced a grand_total ~$67 over
        # the vendor's actual balance due).
        self.scanned_ceiling: Decimal | None = None
        # module_name -> set of str(uuid) this turn has actually seen, via
        # search/resolve/get/list/create. Nothing else may reference an id.
        self.provenance: dict[str, set[str]] = {}
        self.events: list[dict[str, Any]] = []  # one entry per dispatched tool call, for the audit log + UI receipts

    def _remember(self, module: str, *ids: str) -> None:
        self.provenance.setdefault(module, set()).update(ids)

    def _seen(self, module: str, record_id: str) -> bool:
        return record_id in self.provenance.get(module, set())

    def _require_permission(self, module: str, action: str) -> None:
        if self.user.is_admin:
            return
        if not self.user.module_permissions.get(module, {}).get(action):
            raise ToolError(f"not permitted: {action} on {module}")

    def _module(self, name: str) -> ModuleMetadata:
        try:
            return self.registry.get(name)
        except KeyError:
            raise ToolError(f"no such module: {name}") from None

    def _write_allowed(self, module: str) -> dict | None:
        """Returns the module's write-allowlist entry ({"module","amount_field"})
        or None if AI writes aren't enabled for it at all."""
        if self.ai_settings is None:
            return None
        for entry in self.ai_settings.write_allowed_modules:
            if entry.get("module") == module:
                return entry
        return None

    def _embedding_parent(self, module_name: str):
        """Returns (parent_module, relationship) if `module_name` is
        embedded as a child grid on some OTHER module, else None. A child
        table's own FieldMetadata never includes the parent-linking FK
        column — see dynamic_tables.resolve_table's docstring — so a
        direct create on the child module has no way to link the new row
        to any parent at all; it can only ever produce an orphan row. This
        is what get_module_directory's "embedded child" listings, and the
        create_record `children` parameter, exist to route around."""
        for other in self.registry.all().values():
            for rel in other.embedded_children():
                if rel.related_module == module_name:
                    return other, rel
        return None


def _record_label(module: ModuleMetadata, row: dict[str, Any]) -> str:
    text_fields = [f for f in module.fields if f.data_type in _SEARCHABLE_TYPES]
    if text_fields and row.get(text_fields[0].name):
        return str(row[text_fields[0].name])
    return str(row.get("id"))


def _compact_row(module: ModuleMetadata, row: dict[str, Any]) -> dict[str, Any]:
    """Trims a full DB row down to id + label + a handful of business
    fields — keeps tool-result payloads (and therefore the LLM's context)
    small across a 40+ module registry. System columns (created_at,
    version, deleted_at, ...) are never useful to the model."""
    system = {"id", "created_at", "updated_at", "created_by", "deleted_at", "version", "client_code"}
    out = {"id": str(row.get("id")), "label": _record_label(module, row)}
    count = 0
    for f in module.fields:
        if f.name in system or count >= 8:
            continue
        if f.name in row and row[f.name] is not None:
            out[f.name] = row[f.name] if not isinstance(row[f.name], (uuid.UUID,)) else str(row[f.name])
            count += 1
    return out


# ---------------------------------------------------------------------------
# System-prompt module directory
# ---------------------------------------------------------------------------


def build_module_directory(registry: SessionModuleRegistry) -> str:
    """Compact per-module summary for the system prompt — name/label, key
    fields (with LOOKUP targets), workflow states/transitions, and embedded
    child grids (with THEIR fields, since a child module's own field list
    never includes the parent-linking FK column — see resolve_table). This
    is what tells the model a line-item module like general_journal_lines
    is written as a `children` array on its parent's create_record call,
    never as its own top-level record (create_record rejects that
    directly). Deliberately NOT the full JSON metadata (too large/noisy
    across 40+ modules); just enough for the model to know what exists and
    how to reference it via the tools, not the full field-by-field schema."""
    embedding_parents = {
        rel.related_module: (module, rel) for module in registry.all().values() for rel in module.embedded_children()
    }
    lines = []
    for module in sorted(registry.all().values(), key=lambda m: m.name):
        if module.hidden:
            continue
        if module.name in embedding_parents:
            # Listed under its parent's "embedded child" line instead —
            # a standalone entry here would invite a direct create_record
            # call, which is exactly the orphan-row mistake this exists
            # to prevent.
            continue
        field_bits = [_field_bit(f) for f in module.fields[:12]]
        line = f"- {module.name} ({module.label}): {', '.join(field_bits)}"
        if module.workflow:
            states = list(module.workflow.get("states", {}).keys())
            transitions = module.workflow.get("transitions", {})
            line += f" | workflow field={module.workflow.get('field')} states={states} transitions={transitions}"
        if module.posting_rules:
            line += f" | posts GL on status='{module.posting_rules.get('trigger_status')}'"
        for rel in module.embedded_children():
            child = registry.get(rel.related_module)
            child_bits = [_field_bit(f) for f in child.fields[:10]]
            line += f" | embedded child '{rel.name}' -> {rel.related_module}: {', '.join(child_bits)}"
        lines.append(line)
    return "\n".join(lines)


def _field_bit(f) -> str:
    bit = f.name
    if f.data_type == FieldDataType.LOOKUP and f.lookup_module:
        bit += f"->{f.lookup_module}"
    if f.required:
        bit += "*"
    return bit


# ---------------------------------------------------------------------------
# Tool schemas (canonical/OpenAI-shaped function-declaration format — see
# infrastructure/llm.py for how these get adapted per provider)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_records",
        "description": "Fuzzy-search a module's own records by free text (vendor name, item description, invoice number, ...). Always call this before referencing any record by name — never guess an id.",
        "parameters": {
            "type": "object",
            "properties": {
                "module": {"type": "string", "description": "Module name, e.g. vendors, items, purchase_orders"},
                "query": {"type": "string"},
            },
            "required": ["module", "query"],
        },
    },
    {
        "name": "resolve_lookup",
        "description": "Search the module a LOOKUP field points to, for the purpose of filling that field on a create_record call. Use this (not search_records) specifically when resolving a name the user gave for a field like vendor_id/item_id/customer_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "module": {"type": "string", "description": "The module you are about to create/update a record in"},
                "field": {"type": "string", "description": "The LOOKUP field name on that module, e.g. vendor_id"},
                "query": {"type": "string"},
            },
            "required": ["module", "field", "query"],
        },
    },
    {
        "name": "get_record",
        "description": "Fetch one record by id. Use to check a record's current status/fields before deciding whether to transition it.",
        "parameters": {
            "type": "object",
            "properties": {"module": {"type": "string"}, "id": {"type": "string"}},
            "required": ["module", "id"],
        },
    },
    {
        "name": "list_records",
        "description": "List recent records in a module, optionally filtered by exact field values. Good for questions like 'what invoices are open for vendor X'.",
        "parameters": {
            "type": "object",
            "properties": {
                "module": {"type": "string"},
                "filters": {"type": "object", "description": "exact-match field:value pairs"},
                "limit": {"type": "integer"},
            },
            "required": ["module"],
        },
    },
    {
        "name": "create_record",
        "description": (
            "Create a new record. Any LOOKUP field's value MUST be an id returned by resolve_lookup/search_records "
            "earlier in this conversation turn — never invent one. If the module directory lists this module with "
            "'embedded child' relationships (e.g. a journal entry's line items), pass those line rows in `children` "
            "in this SAME call — do NOT call create_record on the child module directly, it will be rejected, since "
            "a child row has no way to link itself to a parent on its own."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "module": {"type": "string"},
                "data": {"type": "object", "description": "field_name: value pairs for the record itself"},
                "children": {
                    "type": "object",
                    "description": (
                        "Only for modules with 'embedded child' relationships. Maps relationship name (e.g. "
                        "'lines') to a list of row objects for that child module, e.g. "
                        "{\"lines\": [{\"account_id\": \"...\", \"debit\": 1000, \"credit\": 0}, "
                        "{\"account_id\": \"...\", \"debit\": 0, \"credit\": 1000}]}"
                    ),
                },
            },
            "required": ["module", "data"],
        },
    },
    {
        "name": "transition_record",
        "description": "Move a record's workflow status forward (e.g. draft -> posted). This is what actually posts a document to the GL if the module has posting rules on that status. The record id must have come from search_records/get_record/create_record earlier this turn.",
        "parameters": {
            "type": "object",
            "properties": {
                "module": {"type": "string"},
                "id": {"type": "string"},
                "to_status": {"type": "string"},
            },
            "required": ["module", "id", "to_status"],
        },
    },
    {
        "name": "get_conversation_history",
        "description": (
            "Fetch the message transcript of one of the CURRENT USER's OTHER saved chats in this same "
            "organization, by its chat number (e.g. the user says 'chat 1', 'in chat #2', 'like we discussed in "
            "chat 3'). Use this whenever the user references a previous chat by number, so you can see what was "
            "actually said there instead of guessing — e.g. to figure out what 'vendor 3' meant in chat 1, read "
            "that transcript and count the vendors mentioned in it."
        ),
        "parameters": {
            "type": "object",
            "properties": {"seq_number": {"type": "integer", "description": "the chat number referenced, e.g. 1 for 'chat 1'"}},
            "required": ["seq_number"],
        },
    },
    {
        "name": "run_report",
        "description": "Run a financial report. report_type is one of: trial_balance, income_statement, balance_sheet, subledger_reconciliation, aging, adhoc. Date params are ISO YYYY-MM-DD.",
        "parameters": {
            "type": "object",
            "properties": {
                "report_type": {"type": "string"},
                "as_of_date": {"type": "string"},
                "date_from": {"type": "string"},
                "date_to": {"type": "string"},
                "group": {"type": "string", "description": "AP or AR, for aging"},
                "adhoc_definition": {"type": "object", "description": "for report_type=adhoc: {source_module, group_by, measures, filters}"},
            },
            "required": ["report_type"],
        },
    },
]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


async def dispatch_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    handler = _HANDLERS.get(name)
    if handler is None:
        raise ToolError(f"unknown tool: {name}")
    try:
        return await handler(args, ctx)
    except (KeyError, TypeError, ValueError) as exc:
        # A handler indexing a required arg (args["module"], etc.) is the
        # one place a malformed tool call from the model — a missing or
        # wrong-shaped argument, not a hallucinated id (that's the
        # provenance check's job) — would otherwise surface as an
        # unhandled crash instead of a plain rejected tool result the
        # model can see and correct on its next attempt.
        raise ToolError(f"malformed arguments for {name}: {exc}") from exc


async def _search_records(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    module_name, query = args["module"], args.get("query", "")
    module = ctx._module(module_name)
    ctx._require_permission(module_name, "read")
    text_fields = [f for f in module.fields if f.data_type in _SEARCHABLE_TYPES]
    if not text_fields:
        return {"results": []}
    table = resolve_table(module, ctx.registry)
    conditions = [table.c[f.name].ilike(f"%{query}%") for f in text_fields if f.name in table.c]
    conds = [table.c.deleted_at.is_(None)]
    if conditions:
        conds.append(or_(*conditions))
    if "client_code" in table.c:
        conds.append(table.c.client_code == ctx.repo.client_code)
    rows = (await ctx.session.execute(select(table).where(*conds).limit(_SEARCH_LIMIT))).mappings().all()
    results = [_compact_row(module, dict(r)) for r in rows]
    ctx._remember(module_name, *(r["id"] for r in results))
    return {"results": results}


async def _resolve_lookup(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    module = ctx._module(args["module"])
    field = module.field(args["field"])
    if field is None or field.data_type != FieldDataType.LOOKUP or not field.lookup_module:
        raise ToolError(f"{args['field']} is not a LOOKUP field on {args['module']}")
    return await _search_records({"module": field.lookup_module, "query": args.get("query", "")}, ctx)


async def _get_record(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    module_name = args["module"]
    module = ctx._module(module_name)
    ctx._require_permission(module_name, "read")
    try:
        record_id = uuid.UUID(str(args["id"]))
    except ValueError:
        raise ToolError("id is not a valid uuid") from None
    row = await ctx.repo.get(module_name, record_id)
    if row is None:
        raise ToolError("record not found")
    ctx._remember(module_name, str(record_id))
    return {"record": _compact_row(module, row)}


async def _list_records(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    module_name = args["module"]
    module = ctx._module(module_name)
    ctx._require_permission(module_name, "read")
    limit = min(int(args.get("limit") or _LIST_LIMIT), _LIST_LIMIT)
    rows = await ctx.repo.list(module_name, filters=args.get("filters") or {}, limit=limit)
    results = [_compact_row(module, r) for r in rows]
    ctx._remember(module_name, *(r["id"] for r in results))
    return {"results": results}


def _posting_child_relations(module: ModuleMetadata) -> set[str]:
    """Embedded relationship names this module's posting_rules reads GL
    lines from — per_child/per_child_grouped rule types name the relation
    directly. synthetic_grouped isn't included: it reads a precomputed
    {group: amount} dict off the record itself (set by the stock engine
    post-movement), not a child relation the AI could ever populate."""
    if not module.posting_rules:
        return set()
    return {
        rule["child_relation"]
        for rule in module.posting_rules.get("lines", [])
        if rule.get("type") in ("per_child", "per_child_grouped") and rule.get("child_relation")
    }


def _to_decimal(raw: Any) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return None


def _has_nonzero_amount(row: dict[str, Any]) -> bool:
    for v in row.values():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float, Decimal)) and v != 0:
            return True
        if isinstance(v, str):
            try:
                if Decimal(v) != 0:
                    return True
            except InvalidOperation:
                continue
    return False


def _check_lookup_provenance(module: ModuleMetadata, module_name: str, row: dict[str, Any], ctx: ToolContext) -> None:
    for f in module.fields:
        if f.data_type == FieldDataType.LOOKUP and f.name in row and row[f.name]:
            if not ctx._seen(f.lookup_module or "", str(row[f.name])):
                raise ToolError(
                    f"the value for '{f.name}' on {module_name} must come from resolve_lookup(module='{module_name}', "
                    f"field='{f.name}', ...) called earlier this turn — call it first, then retry create_record"
                )


async def _create_record(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    module_name = args["module"]
    module = ctx._module(module_name)

    embedding = ctx._embedding_parent(module_name)
    if embedding is not None:
        parent, rel = embedding
        raise ToolError(
            f"'{module_name}' is an embedded child of '{parent.name}' (relationship '{rel.name}') — it has no way "
            f"to link itself to a parent on its own. Create it together with the parent instead: call create_record "
            f"on module='{parent.name}' with children={{'{rel.name}': [<row>, ...]}}."
        )

    ctx._require_permission(module_name, "create")
    if ctx._write_allowed(module_name) is None:
        raise ToolError(f"AI writes are not enabled for module '{module_name}' — ask an admin to allow it in AI Assistant settings")

    data = dict(args.get("data") or {})
    _check_lookup_provenance(module, module_name, data, ctx)

    children_arg = args.get("children") or {}
    embedded_by_name = {rel.name: rel for rel in module.embedded_children()}
    child_diffs: dict[str, ChildDiff] = {}
    for rel_name, rows in children_arg.items():
        rel = embedded_by_name.get(rel_name)
        if rel is None:
            raise ToolError(f"'{rel_name}' is not an embedded relationship on {module_name}")
        child_module = ctx._module(rel.related_module)
        rows = list(rows or [])
        for row in rows:
            _check_lookup_provenance(child_module, rel.related_module, row, ctx)
        child_diffs[rel_name] = ChildDiff(create=rows)

    # A module that posts to the GL from its own line items (a journal
    # entry, an invoice) but gets created with no lines — or lines that
    # are all zero — isn't a data-entry mistake a human would make through
    # the real UI (EmbeddedGrid won't let you save a blank line), but it's
    # exactly the shape of mistake an under-specified request ("post
    # journal", no amount given) produces here. posting.post_document()
    # itself correctly treats "every line is zero" as a legitimate no-op
    # for a human-initiated transition (a service-only delivery really can
    # have nothing to post) — so this can't be fixed there without
    # breaking that. Caught here instead, deterministically, before the
    # record (and its GL non-impact) is ever created.
    for rel_name in _posting_child_relations(module):
        rows = child_diffs[rel_name].create if rel_name in child_diffs else []
        if not rows or not any(_has_nonzero_amount(r) for r in rows):
            raise ToolError(
                f"'{module_name}' posts to the general ledger from its '{rel_name}' line items, but no lines with "
                f"a non-zero amount were given. Ask the user for the actual amounts and accounts before creating "
                f"this document — never create or post one with empty or all-zero lines."
            )

    try:
        row = await ctx.repo.create(module_name, data, child_diffs or None)
    except (CreateGuardBlocked, LookupScopeError) as exc:
        raise ToolError(str(getattr(exc, "message", exc))) from exc

    if ctx.scanned_ceiling is not None and module.clearing_config:
        amount_field = module.clearing_config.get("amount_field")
        recorded = _to_decimal(row.get(amount_field)) if amount_field else None
        if recorded is not None:
            tolerance = max(Decimal("1"), ctx.scanned_ceiling * Decimal("0.01"))
            if recorded > ctx.scanned_ceiling + tolerance:
                await ctx.repo.delete(module_name, uuid.UUID(str(row["id"])))
                raise ToolError(
                    f"BLOCKED before creating: the {amount_field} this record would have ({recorded}) exceeds the "
                    f"scanned document's own total ({ctx.scanned_ceiling}) by more than a rounding tolerance. The "
                    f"attempted record was NOT kept. This almost always means a discount, credit, or reduction "
                    f"shown on the document wasn't captured — re-check the extraction for discount_total (header) "
                    f"or a line's discount_amount, set the invoice's discount_amount / that line's discount_percent "
                    f"accordingly, and retry create_record. If you truly cannot reconcile it, stop and ask the user "
                    f"to confirm the correct total instead of creating an inflated record."
                )

    ctx._remember(module_name, str(row["id"]))
    return {"created": _compact_row(module, row)}


async def _transition_record(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    module_name = args["module"]
    module = ctx._module(module_name)
    ctx._require_permission(module_name, "update")
    record_id_str = str(args["id"])
    if not ctx._seen(module_name, record_id_str):
        raise ToolError("that record id hasn't been looked up this turn — call get_record or search_records first, then retry")
    allow_entry = ctx._write_allowed(module_name)
    if allow_entry is None:
        raise ToolError(f"AI writes are not enabled for module '{module_name}' — ask an admin to allow it in AI Assistant settings")

    to_status = args["to_status"]
    is_posting_trigger = bool(module.posting_rules) and module.posting_rules.get("trigger_status") == to_status
    amount_field = allow_entry.get("amount_field")
    cap = ctx.ai_settings.auto_post_amount_cap if ctx.ai_settings else None
    if is_posting_trigger and amount_field and cap is not None:
        row = await ctx.repo.get(module_name, uuid.UUID(record_id_str))
        raw_amount = (row or {}).get(amount_field)
        try:
            amount = Decimal(str(raw_amount)) if raw_amount is not None else None
        except InvalidOperation:
            amount = None
        if amount is not None and amount > cap:
            return {
                "status": "requires_confirmation",
                "reason": f"{amount_field}={amount} exceeds the auto-post cap of {cap} — ask the user to confirm before posting",
                "module": module_name,
                "id": record_id_str,
                "to_status": to_status,
            }

    try:
        row = await ctx.repo.transition(module_name, uuid.UUID(record_id_str), to_status)
    except ApprovalRequiredError as exc:
        # Same rule the regular UI hits (WorkflowBar.svelte's "file an
        # approval request" fallback) — the assistant can't push this
        # through on its own either, so it's surfaced the same way the
        # amount cap is: stop and tell the user, don't file the request
        # automatically on their behalf.
        return {
            "status": "requires_approval",
            "reason": str(exc),
            "module": module_name,
            "id": record_id_str,
            "to_status": to_status,
        }
    except ConcurrencyConflict as exc:
        raise ToolError(str(exc)) from exc
    except PermissionError as exc:
        raise ToolError(str(exc)) from exc
    ctx._remember(module_name, str(row["id"]))
    return {"status": "executed", "record": _compact_row(module, row)}


async def _get_conversation_history(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    seq_number = int(args["seq_number"])
    convo = (
        await ctx.session.execute(
            select(AiConversation).where(
                AiConversation.user_id == uuid.UUID(ctx.user.id),
                AiConversation.client_code == ctx.repo.client_code,
                AiConversation.seq_number == seq_number,
            )
        )
    ).scalar_one_or_none()
    if convo is None:
        raise ToolError(f"no chat #{seq_number} found for this user in this organization")
    messages = (
        await ctx.session.execute(
            select(AiConversationMessage)
            .where(AiConversationMessage.conversation_id == convo.id)
            .order_by(AiConversationMessage.created_at.asc())
        )
    ).scalars().all()
    return {"seq_number": seq_number, "title": convo.title, "messages": [{"role": m.role, "content": m.content} for m in messages]}


async def _run_report(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    ctx._require_permission("gl_accounts", "read")
    report_type = args["report_type"]
    client_code = ctx.repo.client_code
    if report_type == "trial_balance":
        return await financial_reports.trial_balance(ctx.session, ctx.registry, client_code=client_code, as_of_date=_date(args, "as_of_date"))
    if report_type == "income_statement":
        return await financial_reports.income_statement(
            ctx.session, ctx.registry, client_code=client_code, date_from=_date(args, "date_from"), date_to=_date(args, "date_to")
        )
    if report_type == "balance_sheet":
        return await financial_reports.balance_sheet(ctx.session, ctx.registry, client_code=client_code, as_of_date=_date(args, "as_of_date"))
    if report_type == "subledger_reconciliation":
        return await financial_reports.subledger_reconciliation(ctx.session, ctx.registry, client_code=client_code, as_of_date=_date(args, "as_of_date"))
    if report_type == "aging":
        rows = await financial_reports.aging_report(
            ctx.session, ctx.registry, client_code=client_code, group=args.get("group", "AP"), as_of_date=_date(args, "as_of_date")
        )
        return {"rows": rows}
    if report_type == "adhoc":
        definition = args.get("adhoc_definition") or {}
        source_module = definition.get("source_module")
        if source_module:
            ctx._require_permission(source_module, "read")
        rows = await adhoc_reports.run_report(ctx.session, ctx.registry, definition, client_code=client_code)
        return {"rows": rows}
    raise ToolError(f"unknown report_type: {report_type}")


def _date(args: dict[str, Any], key: str):
    from datetime import date

    raw = args.get(key)
    if not raw:
        return date.today()
    return date.fromisoformat(raw)


_HANDLERS = {
    "search_records": _search_records,
    "resolve_lookup": _resolve_lookup,
    "get_record": _get_record,
    "list_records": _list_records,
    "create_record": _create_record,
    "transition_record": _transition_record,
    "get_conversation_history": _get_conversation_history,
    "run_report": _run_report,
}
