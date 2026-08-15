from metaforge_api.domain.metadata import (
    FieldDataType,
    FieldMetadata,
    ModuleMetadata,
    ModuleRelationship,
    RelationshipType,
)
from metaforge_api.domain.schema_diff import (
    AddColumnOp,
    AddParentForeignKeyOp,
    CreateTableOp,
    plan_schema_diff,
)


def _field(name, dtype=FieldDataType.TEXT, required=False):
    return FieldMetadata(name=name, label=name, data_type=dtype, control_type="text", required=required)


def test_new_module_produces_create_table():
    module = ModuleMetadata(name="orders", label="Orders", fields=(_field("customer_name"),))
    plan = plan_schema_diff(None, module)
    assert len(plan.operations) == 1
    assert isinstance(plan.operations[0], CreateTableOp)
    assert not plan.warnings


def test_adding_a_field_produces_add_column():
    old = ModuleMetadata(name="orders", label="Orders", fields=(_field("customer_name"),), version=1)
    new = ModuleMetadata(
        name="orders", label="Orders", fields=(_field("customer_name"), _field("notes")), version=2
    )
    plan = plan_schema_diff(old, new)
    assert plan.operations == (AddColumnOp(module_name="orders", field=new.field("notes")),)


def test_removing_a_field_warns_but_does_not_drop():
    old = ModuleMetadata(name="orders", label="Orders", fields=(_field("customer_name"), _field("notes")))
    new = ModuleMetadata(name="orders", label="Orders", fields=(_field("customer_name"),))
    plan = plan_schema_diff(old, new)
    assert plan.operations == ()
    assert plan.has_destructive_changes
    assert "notes" in plan.warnings[0].reason


def test_retyping_a_field_warns():
    old = ModuleMetadata(name="orders", label="Orders", fields=(_field("qty", FieldDataType.TEXT),))
    new = ModuleMetadata(name="orders", label="Orders", fields=(_field("qty", FieldDataType.INTEGER),))
    plan = plan_schema_diff(old, new)
    assert plan.has_destructive_changes


def test_new_embedded_relationship_produces_parent_fk_op():
    rel = ModuleRelationship(
        name="items",
        type=RelationshipType.ONE_TO_MANY,
        related_module="order_items",
        foreign_key="order_id",
        embedded=True,
        cascade_delete=True,
    )
    old = ModuleMetadata(name="orders", label="Orders", fields=(_field("customer_name"),))
    new = ModuleMetadata(name="orders", label="Orders", fields=(_field("customer_name"),), relationships=(rel,))
    plan = plan_schema_diff(old, new)
    assert plan.operations == (
        AddParentForeignKeyOp(
            child_module_name="order_items",
            parent_module_name="orders",
            fk_column_name="order_id",
            cascade_delete=True,
        ),
    )


def test_removing_a_relationship_warns():
    rel = ModuleRelationship(
        name="items", type=RelationshipType.ONE_TO_MANY, related_module="order_items", foreign_key="order_id"
    )
    old = ModuleMetadata(name="orders", label="Orders", fields=(), relationships=(rel,))
    new = ModuleMetadata(name="orders", label="Orders", fields=())
    plan = plan_schema_diff(old, new)
    assert plan.has_destructive_changes
