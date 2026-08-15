"""Pure dict <-> ModuleMetadata (de)serialization, shared by the JSONB
`modules.metadata` column and the FastAPI builder API. No sqlalchemy /
fastapi imports — keeps ModuleMetadata storable and transmittable without
coupling the domain layer to either.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from metaforge_api.domain.metadata import (
    AggregateOp,
    CopyFromLookup,
    DefaultFromLookup,
    FieldAggregate,
    FieldCondition,
    FieldDataType,
    FieldMetadata,
    LookupFilter,
    ModuleMetadata,
    ModuleRelationship,
    PriceFromList,
    RelationshipType,
)


def module_to_dict(module: ModuleMetadata) -> dict[str, Any]:
    d = asdict(module)
    for f in d["fields"]:
        f["data_type"] = FieldDataType(f["data_type"]).value
        if f["aggregate"] is not None:
            f["aggregate"]["op"] = AggregateOp(f["aggregate"]["op"]).value
    for r in d["relationships"]:
        r["type"] = RelationshipType(r["type"]).value
    return d


def module_from_dict(d: dict[str, Any]) -> ModuleMetadata:
    fields = tuple(_field_from_dict(f) for f in d.get("fields", []))
    relationships = tuple(_relationship_from_dict(r) for r in d.get("relationships", []))
    return ModuleMetadata(
        name=d["name"],
        label=d["label"],
        fields=fields,
        relationships=relationships,
        version=d.get("version", 1),
        workflow=d.get("workflow"),
        posting_rules=d.get("posting_rules"),
        clearing_config=d.get("clearing_config"),
        stock_rules=d.get("stock_rules"),
        document_flows=d.get("document_flows"),
        detail_actions=d.get("detail_actions"),
        create_guards=d.get("create_guards"),
        hidden=d.get("hidden", False),
    )


def _field_from_dict(f: dict[str, Any]) -> FieldMetadata:
    aggregate = f.get("aggregate")
    conditions = f.get("conditions") or []
    return FieldMetadata(
        name=f["name"],
        label=f["label"],
        data_type=FieldDataType(f["data_type"]),
        control_type=f["control_type"],
        required=f.get("required", False),
        unique=f.get("unique", False),
        read_only=f.get("read_only", False),
        is_default_flag=f.get("is_default_flag", False),
        is_period_gate=f.get("is_period_gate", False),
        default=f.get("default"),
        enum_values=tuple(f["enum_values"]) if f.get("enum_values") else None,
        lookup_module=f.get("lookup_module"),
        formula=f.get("formula"),
        aggregate=FieldAggregate(
            from_module=aggregate["from_module"],
            foreign_key=aggregate["foreign_key"],
            source_field=aggregate["source_field"],
            op=AggregateOp(aggregate["op"]),
            filter_field=aggregate.get("filter_field"),
            filter_value=aggregate.get("filter_value"),
        )
        if aggregate
        else None,
        conditions=tuple(
            FieldCondition(
                when_field=c["when_field"],
                equals=c.get("equals"),
                then_visible=c.get("then_visible"),
                then_read_only=c.get("then_read_only"),
                then_required=c.get("then_required"),
            )
            for c in conditions
        ),
        max_length=f.get("max_length"),
        precision=f.get("precision"),
        scale=f.get("scale"),
        default_from_lookup=DefaultFromLookup(
            lookup_field=f["default_from_lookup"]["lookup_field"],
            term_field=f["default_from_lookup"]["term_field"],
            term_days=f["default_from_lookup"]["term_days"],
            base_date_field=f["default_from_lookup"]["base_date_field"],
        )
        if f.get("default_from_lookup")
        else None,
        copy_from_lookup=CopyFromLookup(
            lookup_field=f["copy_from_lookup"]["lookup_field"],
            source_field=f["copy_from_lookup"]["source_field"],
        )
        if f.get("copy_from_lookup")
        else None,
        price_from_list=PriceFromList(
            price_list_module=f["price_from_list"]["price_list_module"],
            header_party_field=f["price_from_list"]["header_party_field"],
            item_field=f["price_from_list"]["item_field"],
            qty_field=f["price_from_list"]["qty_field"],
        )
        if f.get("price_from_list")
        else None,
        lookup_filter=LookupFilter(
            by_field=f["lookup_filter"]["by_field"],
            from_field=f["lookup_filter"]["from_field"],
        )
        if f.get("lookup_filter")
        else None,
        group=f.get("group"),
    )


def _relationship_from_dict(r: dict[str, Any]) -> ModuleRelationship:
    return ModuleRelationship(
        name=r["name"],
        type=RelationshipType(r["type"]),
        related_module=r["related_module"],
        foreign_key=r["foreign_key"],
        embedded=r.get("embedded", False),
        cascade_delete=r.get("cascade_delete", False),
        join_module=r.get("join_module"),
        left_field=r.get("left_field"),
        right_field=r.get("right_field"),
    )
