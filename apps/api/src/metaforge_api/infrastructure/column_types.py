"""FieldDataType -> SQLAlchemy column type mapping, per the plan's field-type table."""

from __future__ import annotations

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import Integer, TypeEngine

from metaforge_api.domain.metadata import FieldDataType, FieldMetadata

_SIMPLE_TYPES: dict[FieldDataType, type[TypeEngine]] = {
    FieldDataType.TEXT: String,
    FieldDataType.EMAIL: String,
    FieldDataType.PHONE: String,
    FieldDataType.URL: String,
    FieldDataType.LONG_TEXT: Text,
    FieldDataType.RICH_TEXT: Text,
    FieldDataType.INTEGER: Integer,
    FieldDataType.DATE: Date,
    FieldDataType.TIME: Time,
    FieldDataType.BOOLEAN: Boolean,
    FieldDataType.JSON: JSONB,
    # Stores the *formatted* value ("PO-0001"), not a raw counter — the
    # counter itself lives in number_series.next_value (an actual integer).
    # This column just holds whatever _allocate_number_series() renders,
    # prefix and zero-padding included, so it has to be a string column.
    FieldDataType.AUTO_NUMBER: String,
}

_TIMESTAMPTZ_TYPES = {FieldDataType.DATETIME}
_NUMERIC_TYPES = {FieldDataType.DECIMAL, FieldDataType.MONEY, FieldDataType.PERCENT}
_UUID_FK_TYPES = {FieldDataType.LOOKUP, FieldDataType.FILE, FieldDataType.IMAGE}


def column_type_for_field(field: FieldMetadata) -> TypeEngine:
    if field.data_type in _NUMERIC_TYPES:
        precision = field.precision or 18
        scale = field.scale or 4
        return Numeric(precision, scale)
    if field.data_type in _TIMESTAMPTZ_TYPES:
        return DateTime(timezone=True)
    if field.data_type in _UUID_FK_TYPES:
        return UUID(as_uuid=True)
    if field.data_type == FieldDataType.ENUM:
        return String(field.max_length or 64)
    simple = _SIMPLE_TYPES.get(field.data_type)
    if simple is None:
        raise ValueError(f"no column type mapping for {field.data_type}")
    if simple is String:
        return String(field.max_length or 255)
    return simple()


def is_foreign_key_field(field: FieldMetadata) -> bool:
    return field.data_type in _UUID_FK_TYPES
