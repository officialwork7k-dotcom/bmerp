"""Regression test for a real bug found during Part 2 authoring: a bare
build_table(child_module) call is missing the parent_id FK column that only
exists because some OTHER module embeds it — that column is attached by
resolve_table()/DataRepository._table_for(), never by build_table() alone.
Every engine module (posting/stock/document_flow/clearing/reports) that
resolves an arbitrary module's table for reading must go through
resolve_table(), not build_table() directly, or it silently depends on some
earlier unrelated call having already mutated the shared table cache.
"""

from metaforge_api.domain.metadata import (
    FieldDataType,
    FieldMetadata,
    ModuleMetadata,
    ModuleRelationship,
    RelationshipType,
)
from metaforge_api.infrastructure.dynamic_tables import build_table, resolve_table


class _FakeRegistry:
    def __init__(self, modules):
        self._modules = {m.name: m for m in modules}

    def get(self, name):
        return self._modules[name]

    def all(self):
        return dict(self._modules)


def _parent_child_modules(suffix: str):
    child = ModuleMetadata(
        name=f"rt_child_{suffix}",
        label="Child",
        fields=(FieldMetadata(name="qty", label="Qty", data_type=FieldDataType.INTEGER, control_type="number"),),
    )
    parent = ModuleMetadata(
        name=f"rt_parent_{suffix}",
        label="Parent",
        fields=(),
        relationships=(
            ModuleRelationship(
                name="lines", type=RelationshipType.ONE_TO_MANY, related_module=child.name,
                foreign_key="parent_id", embedded=True,
            ),
        ),
    )
    return parent, child


def test_bare_build_table_is_missing_the_parent_fk_column():
    parent, child = _parent_child_modules("bare")
    registry = _FakeRegistry([parent, child])
    table = build_table(child)  # deliberately NOT resolve_table — this is the bug being guarded against
    assert "parent_id" not in table.c


def test_resolve_table_attaches_the_parent_fk_column():
    parent, child = _parent_child_modules("resolved")
    registry = _FakeRegistry([parent, child])
    table = resolve_table(child, registry)
    assert "parent_id" in table.c


def test_resolve_table_is_safe_to_call_repeatedly():
    parent, child = _parent_child_modules("repeat")
    registry = _FakeRegistry([parent, child])
    first = resolve_table(child, registry)
    second = resolve_table(child, registry)
    assert "parent_id" in first.c
    assert "parent_id" in second.c
