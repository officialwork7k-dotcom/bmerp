from datetime import date, datetime

from metaforge_api.domain.metadata import FieldDataType, FieldMetadata, ModuleMetadata
from metaforge_api.infrastructure.repository import coerce_row


def _field(name, dtype):
    return FieldMetadata(name=name, label=name, data_type=dtype, control_type="")


MODULE = ModuleMetadata(
    name="purchase_orders",
    label="Purchase Orders",
    fields=(
        _field("order_date", FieldDataType.DATE),
        _field("created_at_ts", FieldDataType.DATETIME),
        _field("status", FieldDataType.TEXT),
    ),
)


def test_date_string_becomes_date_object():
    out = coerce_row(MODULE, {"order_date": "2026-08-01"})
    assert out["order_date"] == date(2026, 8, 1)


def test_datetime_string_with_z_suffix_becomes_datetime_object():
    out = coerce_row(MODULE, {"created_at_ts": "2026-08-01T10:30:00Z"})
    assert out["created_at_ts"] == datetime.fromisoformat("2026-08-01T10:30:00+00:00")


def test_non_date_fields_pass_through_unchanged():
    out = coerce_row(MODULE, {"status": "sent"})
    assert out["status"] == "sent"


def test_none_values_pass_through():
    out = coerce_row(MODULE, {"order_date": None})
    assert out["order_date"] is None
