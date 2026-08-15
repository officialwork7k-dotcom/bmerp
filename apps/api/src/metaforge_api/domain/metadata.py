"""Plain-Python metadata model for MetaForge modules.

No fastapi / sqlalchemy imports here — this is the framework-agnostic domain
layer. Infrastructure code translates these dataclasses into SQLAlchemy
Table objects and Alembic DDL; API code translates them into Pydantic
request/response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FieldDataType(str, Enum):
    TEXT = "TEXT"
    LONG_TEXT = "LONG_TEXT"
    RICH_TEXT = "RICH_TEXT"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    MONEY = "MONEY"
    PERCENT = "PERCENT"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"
    LOOKUP = "LOOKUP"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    JSON = "JSON"
    FILE = "FILE"
    IMAGE = "IMAGE"
    AUTO_NUMBER = "AUTO_NUMBER"


class RelationshipType(str, Enum):
    ONE_TO_MANY = "ONE_TO_MANY"
    ONE_TO_ONE = "ONE_TO_ONE"
    MANY_TO_MANY = "MANY_TO_MANY"


class AggregateOp(str, Enum):
    SUM = "sum"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    AVG = "avg"


@dataclass(frozen=True)
class FieldAggregate:
    from_module: str
    foreign_key: str
    source_field: str
    op: AggregateOp
    # Optional rollup filter: only child rows where `filter_field ==
    # filter_value` are included — e.g. an "open_balance" field summing only
    # unpaid invoice lines. `None` (the default) means every non-deleted
    # child row, matching v1 behavior exactly.
    filter_field: str | None = None
    filter_value: object = None


@dataclass(frozen=True)
class DefaultFromLookup:
    """Declarative "smart default": compute this field's value from a
    related record reached through one of this module's own LOOKUP fields,
    rather than a static literal. The motivating case is an invoice's due
    date, which should default from whatever payment terms are on file for
    the vendor/customer it's billed to — not something a clerk should have
    to compute and type by hand, and not a *fixed* default either, since it
    depends on which vendor is selected.

    `term_days` maps the related record's `term_field` value (e.g. a
    vendor's `payment_terms` ENUM value "NET30") to an integer day offset
    added to this row's own `base_date_field` (e.g. `invoice_date`). Only
    applied when the target field has no value yet — an explicit value the
    user typed is never overwritten."""

    lookup_field: str
    term_field: str
    term_days: dict
    base_date_field: str


@dataclass(frozen=True)
class CopyFromLookup:
    """Declarative "copy this field from whatever this row's LOOKUP field
    points to" — the generic version of what used to be a hardcoded
    "if this LOOKUP field changes, copy the related record's `description`
    into a field literally named `description`" special case in
    EmbeddedGrid.svelte. Now any field can declare where its value should
    be copied from (an Items line's `description` from `item.description`,
    an invoice line's `tax_rate` from `tax_code_id.rate`), and the frontend
    just follows the declaration instead of hardcoding field names. Applied
    client-side, live, as the user edits a grid — and applies to any row
    that arrives with the lookup field already set but this field empty
    (a document-flow pull, a CSV import), not just a manual cell edit."""

    lookup_field: str
    source_field: str


@dataclass(frozen=True)
class PriceFromList:
    """Declarative "resolve my value from a price list" — the minimal
    price-list pattern (most-specific-match on party+item+qty-break),
    deliberately not SAP's full condition-technique. `header_party_field`
    names the field on this row's *parent document* (not this line) that
    identifies the vendor/customer — a line only knows its own item/qty,
    the party is on the header, so the frontend has to be handed the
    header's current values alongside the grid to resolve this at all.
    `item_field`/`qty_field` name the fields on this same line row. Applied
    only when this field is still empty, same rule as copy_from_lookup."""

    price_list_module: str
    header_party_field: str
    item_field: str
    qty_field: str


@dataclass(frozen=True)
class LookupFilter:
    """Declarative "narrow this LOOKUP's candidates to ones that match a
    sibling field already selected on this same record" — e.g. a Vendor
    Invoice's Purchase Order picker should only offer POs for the vendor
    already chosen on the invoice. `by_field` names a column on the
    lookup_module's own table; `from_field` names the field on *this*
    record whose current value that column must equal. Resolved client-side
    as an extra `?by_field=value` query param on the same search request —
    the backend's generic column-equality filter (repository.list's
    `filters` dict) already supports this with no server-side change."""

    by_field: str
    from_field: str


@dataclass(frozen=True)
class FieldCondition:
    when_field: str
    equals: object
    then_visible: bool | None = None
    then_read_only: bool | None = None
    then_required: bool | None = None


@dataclass(frozen=True)
class FieldMetadata:
    name: str
    label: str
    data_type: FieldDataType
    control_type: str
    required: bool = False
    unique: bool = False
    read_only: bool = False
    # Only meaningful on a BOOLEAN field: marks it as a module-wide "exactly
    # one record may have this set" flag (default localization profile,
    # default warehouse, default number series, ...). Enforced at the DB
    # level by a partial unique index (see schema_sync.py) and by
    # unset-the-others transaction logic in repository.py — never just a
    # UI convention, since two people saving concurrently must not be able
    # to both end up "the default."
    is_default_flag: bool = False
    # Marks a DATE/DATETIME field as the one that determines which fiscal
    # period a record belongs to (e.g. an invoice's "posting_date"). At most
    # one field per module should set this — repository.py's period-gate
    # check uses the first one it finds. See infrastructure/fiscal.py.
    is_period_gate: bool = False
    default: object = None
    enum_values: tuple[str, ...] | None = None
    lookup_module: str | None = None
    formula: str | None = None
    aggregate: FieldAggregate | None = None
    conditions: tuple[FieldCondition, ...] = ()
    max_length: int | None = None
    precision: int | None = None
    scale: int | None = None
    default_from_lookup: DefaultFromLookup | None = None
    copy_from_lookup: CopyFromLookup | None = None
    price_from_list: PriceFromList | None = None
    lookup_filter: LookupFilter | None = None
    # Purely a form-layout hint for DetailPage/DataForm: fields sharing the
    # same `group` string render together under one titled section (e.g.
    # "Address", "Purchasing", "Accounting") instead of one flat list. `None`
    # (the default) means "General" — ungrouped fields render first, exactly
    # like today, so existing modules are unaffected. Section order follows
    # each group's first-encountered field in `fields` order, not alphabetic,
    # so the builder's field ordering still controls layout.
    group: str | None = None


@dataclass(frozen=True)
class ModuleRelationship:
    name: str
    type: RelationshipType
    related_module: str
    foreign_key: str
    embedded: bool = False
    cascade_delete: bool = False
    join_module: str | None = None
    left_field: str | None = None
    right_field: str | None = None


@dataclass(frozen=True)
class ModuleMetadata:
    name: str
    label: str
    fields: tuple[FieldMetadata, ...]
    relationships: tuple[ModuleRelationship, ...] = ()
    version: int = 1
    # Generic status-machine, not a BPM engine (deliberately out of scope for
    # a 4GB VM — see the "workflow" consultation in this project's history).
    # Shape: {"field": "status", "states": {name: {"color": str, "locked":
    # bool}}, "transitions": {from_state: [to_state, ...]}}. `locked` means
    # every field except the status field itself becomes read-only server-
    # side while a record sits in that state — the ERP invariant that a
    # posted/approved document can't be silently edited.
    workflow: dict | None = None
    # Drives infrastructure/posting.py: fires when `workflow`'s status field
    # transitions to `trigger_status`, generating an immutable journal_entry
    # (+ journal_lines) from this document. Shape: {"trigger_status": str,
    # "date_field": str, "lines": [line-rule, ...]}. Each line-rule is
    # either {"type": "per_child", "child_relation": str, "account_field":
    # str, "account_name_field": str|None, "debit_field": str,
    # "credit_field": str} (one journal line per embedded child row) or
    # {"type": "header", "account_code": str, "account_name": str,
    # "amount_formula": str, "side": "debit"|"credit"} (one line computed
    # from the document's own header fields — amount_formula runs through
    # the same evaluator as FieldMetadata.formula, so it can reference
    # aggregate fields already materialized on the row). See posting.py's
    # module docstring for why this can't be pure metadata like everything
    # else: balance validation and post-time snapshotting are algorithmic,
    # not declarative.
    posting_rules: dict | None = None
    # Drives infrastructure/clearing.py: marks this module's records as
    # "open items" that can be manually matched against other
    # clearing-enabled modules' records (e.g. an AP invoice against the
    # payment(s) that settle it). Shape: {"party_field": str|None,
    # "amount_field": str, "sign": "positive"|"negative"}. `sign` says
    # whether this module's amount increases ("positive", e.g. an invoice
    # increasing what's owed) or decreases ("negative", e.g. a payment) the
    # party's balance — clearing requires the selected items' signed
    # amounts to net to zero. `party_field` (optional) is cross-checked so
    # items from different vendors/customers can't be cleared together.
    clearing_config: dict | None = None
    # Drives infrastructure/stock.py: fires alongside posting_rules on the
    # same workflow transition (e.g. a Goods Receipt moving to "posted"
    # both journals the GR/IR entry AND records the stock receipt). Shape:
    # {"trigger_status": str, "lines": [{"child_relation": str,
    # "item_module": str, "item_field": str, "qty_field": str,
    # "unit_cost_field": str|None, "direction": "in"|"out"}, ...]}. Each
    # line rule walks one embedded child relationship's rows the same way a
    # posting_rules "per_child" line does.
    stock_rules: dict | None = None
    # Drives infrastructure/document_flow.py: metadata-driven "copy this
    # document forward" definitions (PO -> GR -> Invoice, SO -> Delivery ->
    # Invoice) — list of {"name": str, "target_module": str,
    # "header_field_map": {source_field: target_field}, "source_line_
    # relation": str, "target_line_relation": str, "line_field_map":
    # {source_child_field: target_child_field}, "source_qty_field": str,
    # "target_qty_field": str, "tolerance_pct": float}. `tolerance_pct`
    # allows a bounded over-copy (e.g. 5 = up to 5% over the line's
    # remaining open quantity) — 0 means strict "never copy more than what's
    # still open."
    document_flows: list[dict] | None = None
    # Frontend-only config for DetailPage.svelte's record-lifecycle actions
    # (New / Save & New / Save & Close / Duplicate) — every one of those is a
    # framework-level default requiring zero config; this dict exists only
    # to *opt out* per module, never to switch anything on. `None` (the
    # default) means every action is available. Shape: {"disable":
    # ["duplicate", "save_and_new", "save_and_close", "new"], "duplicate":
    # {"copy_lines": bool}}. `duplicate.copy_lines` defaults to False even
    # when duplicate isn't disabled — copying a transactional document's
    # embedded lines (GL postings, GR quantities) is opt-in per module, not
    # a safe default, since it's easy to duplicate quantities/amounts nobody
    # meant to re-create.
    detail_actions: dict | None = None
    # Generic "master data block" enforcement: rejects create_record when a
    # flag on a *related* record is set (vendor.purchasing_blocked stopping
    # new POs, customer.credit_hold stopping new SOs) — the engine-level
    # replacement for hand-rolling this check inside each module's own
    # endpoint. Shape: [{"lookup_field": str (a LOOKUP field on *this*
    # module), "flag_field": str (a BOOLEAN field on the looked-up module),
    # "message": str}]. Evaluated in repository.create_record, in list
    # order, before the insert — the first guard whose flag is true raises
    # a 409 with its message. `lookup_field`'s target module is resolved
    # from that field's own `lookup_module`, so a guard never needs to name
    # it redundantly. Update is intentionally NOT guarded: blocking new
    # documents against a blocked partner is standard ERP behavior, but
    # blocking edits to *existing* documents (e.g. approving/paying one
    # already in flight) is not — that would need its own opt-in.
    create_guards: list[dict] | None = None
    # Hides this module from the sidebar and the top-level Modules list —
    # the module, its table, and its API are otherwise fully functional,
    # unchanged. For modules that only ever exist as an embedded child grid
    # (PO Lines, Invoice Lines) or reference data nobody browses directly,
    # so they don't clutter navigation. Not a permission control — a user
    # with module_permissions can still reach a hidden module by URL.
    hidden: bool = False

    def field(self, name: str) -> FieldMetadata | None:
        return next((f for f in self.fields if f.name == name), None)

    def embedded_children(self) -> tuple[ModuleRelationship, ...]:
        return tuple(
            r
            for r in self.relationships
            if r.embedded and r.type == RelationshipType.ONE_TO_MANY
        )

    def aggregate_fields(self) -> tuple[FieldMetadata, ...]:
        return tuple(f for f in self.fields if f.aggregate is not None)

    def period_gate_field(self) -> FieldMetadata | None:
        return next((f for f in self.fields if f.is_period_gate), None)
