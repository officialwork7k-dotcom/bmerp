"""Additive-only schema diff planner.

Compares a module's previously-applied metadata against its newly-saved
metadata and produces a list of DDL operations plus a list of destructive
changes that are NOT auto-applied (removed/retyped fields, removed
relationships) — those require a manually-authored Alembic revision.

This module is pure data/logic: it has no sqlalchemy or fastapi imports.
`infrastructure/schema_sync.py` turns these operations into real Alembic
`op.*` calls against a specific module's table.
"""

from __future__ import annotations

from dataclasses import dataclass

from metaforge_api.domain.metadata import FieldMetadata, ModuleMetadata, ModuleRelationship


def table_name(module_name: str) -> str:
    return f"biz_{module_name}"


@dataclass(frozen=True)
class CreateTableOp:
    module_name: str
    fields: tuple[FieldMetadata, ...]


@dataclass(frozen=True)
class AddColumnOp:
    module_name: str
    field: FieldMetadata


@dataclass(frozen=True)
class AddDefaultFlagIndexOp:
    """A partial unique index enforcing "at most one row in this module has
    this BOOLEAN field set true" — the DB-level half of the default-record
    mechanism (see FieldMetadata.is_default_flag)."""

    module_name: str
    field_name: str


@dataclass(frozen=True)
class RelaxNotNullOp:
    """Drops a NOT NULL constraint on a column whose field was removed from
    metadata — see the comment where this is emitted in plan_schema_diff."""

    module_name: str
    field_name: str


@dataclass(frozen=True)
class AddParentForeignKeyOp:
    """Adds a typed parent_id column + FK + index to a child module's table."""

    child_module_name: str
    parent_module_name: str
    fk_column_name: str
    cascade_delete: bool


@dataclass(frozen=True)
class DestructiveChangeWarning:
    module_name: str
    reason: str


@dataclass(frozen=True)
class SchemaDiffPlan:
    operations: tuple[object, ...]
    warnings: tuple[DestructiveChangeWarning, ...]

    @property
    def is_empty(self) -> bool:
        return not self.operations and not self.warnings

    @property
    def has_destructive_changes(self) -> bool:
        return bool(self.warnings)


def plan_schema_diff(old: ModuleMetadata | None, new: ModuleMetadata) -> SchemaDiffPlan:
    operations: list[object] = []
    warnings: list[DestructiveChangeWarning] = []

    if old is None:
        operations.append(CreateTableOp(module_name=new.name, fields=new.fields))
        for new_field in new.fields:
            if new_field.is_default_flag:
                operations.append(AddDefaultFlagIndexOp(module_name=new.name, field_name=new_field.name))
    else:
        old_fields = {f.name: f for f in old.fields}
        new_fields = {f.name: f for f in new.fields}

        for name, new_field in new_fields.items():
            if name not in old_fields:
                operations.append(AddColumnOp(module_name=new.name, field=new_field))
                if new_field.is_default_flag:
                    operations.append(AddDefaultFlagIndexOp(module_name=new.name, field_name=name))
            else:
                old_field = old_fields[name]
                if old_field.data_type != new_field.data_type:
                    warnings.append(
                        DestructiveChangeWarning(
                            module_name=new.name,
                            reason=(
                                f"field '{name}' data type changed "
                                f"{old_field.data_type} -> {new_field.data_type}; "
                                "requires a manually-reviewed migration"
                            ),
                        )
                    )
                # Turning the flag on for an already-existing field needs the
                # index created now; turning it off leaves a harmless unused
                # index behind rather than risk an automatic destructive drop.
                if new_field.is_default_flag and not old_field.is_default_flag:
                    operations.append(AddDefaultFlagIndexOp(module_name=new.name, field_name=name))
                # required -> optional needs the DB's NOT NULL relaxed too,
                # or the metadata and the column disagree: the builder says
                # the field is optional but every write still hits a NOT
                # NULL violation. No data loss either way, so this is safe
                # to auto-apply like the field-removal case below.
                if old_field.required and not new_field.required:
                    operations.append(RelaxNotNullOp(module_name=new.name, field_name=name))

        for name in old_fields:
            if name not in new_fields:
                warnings.append(
                    DestructiveChangeWarning(
                        module_name=new.name,
                        reason=f"field '{name}' was removed; column is kept, not dropped automatically",
                    )
                )
                # "Kept, not dropped" is only actually safe if the column
                # can still accept NULL — a required field's column is
                # NOT NULL at the DB level, and once nothing in the app
                # populates it, every future INSERT for this module starts
                # failing outright. Relaxing the constraint loses no data
                # and isn't a "destructive" change by this planner's own
                # definition, so it's safe to auto-apply rather than join
                # the manual-migration warning list.
                if old_fields[name].required:
                    operations.append(RelaxNotNullOp(module_name=new.name, field_name=name))

    old_rel_names = {r.name for r in (old.relationships if old else ())}
    for rel in new.relationships:
        if rel.name in old_rel_names:
            continue
        op = _relationship_to_op(new, rel)
        if op is not None:
            operations.append(op)

    if old is not None:
        new_rel_names = {r.name for r in new.relationships}
        for rel in old.relationships:
            if rel.name not in new_rel_names:
                warnings.append(
                    DestructiveChangeWarning(
                        module_name=new.name,
                        reason=f"relationship '{rel.name}' was removed; FK/constraint is kept, not dropped automatically",
                    )
                )

    return SchemaDiffPlan(operations=tuple(operations), warnings=tuple(warnings))


def _relationship_to_op(parent: ModuleMetadata, rel: ModuleRelationship) -> AddParentForeignKeyOp | None:
    if rel.type.value != "ONE_TO_MANY":
        return None
    return AddParentForeignKeyOp(
        child_module_name=rel.related_module,
        parent_module_name=parent.name,
        fk_column_name=rel.foreign_key,
        cascade_delete=rel.cascade_delete,
    )
