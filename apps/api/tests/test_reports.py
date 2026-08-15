import pytest

from metaforge_api.domain.metadata import FieldDataType, FieldMetadata, ModuleMetadata
from metaforge_api.infrastructure.dynamic_tables import build_table
from metaforge_api.infrastructure.reports import ReportError, _validate_definition


def _module():
    return ModuleMetadata(
        name="test_report_src",
        label="Test",
        fields=(
            FieldMetadata(name="vendor_id", label="Vendor", data_type=FieldDataType.TEXT, control_type="text"),
            FieldMetadata(name="amount", label="Amount", data_type=FieldDataType.MONEY, control_type="number"),
        ),
    )


def test_valid_definition_passes():
    table = build_table(_module())
    _validate_definition(table, {"group_by": ["vendor_id"], "measures": [{"field": "amount", "op": "sum"}], "filters": []})


def test_unknown_group_by_field_rejected():
    table = build_table(_module())
    with pytest.raises(ReportError):
        _validate_definition(table, {"group_by": ["nonexistent"], "measures": [], "filters": []})


def test_unknown_measure_op_rejected():
    table = build_table(_module())
    with pytest.raises(ReportError):
        _validate_definition(table, {"group_by": [], "measures": [{"field": "amount", "op": "median"}], "filters": []})


def test_count_measure_does_not_require_field():
    table = build_table(_module())
    _validate_definition(table, {"group_by": [], "measures": [{"op": "count"}], "filters": []})


def test_unknown_filter_field_rejected():
    table = build_table(_module())
    with pytest.raises(ReportError):
        _validate_definition(table, {"group_by": [], "measures": [], "filters": [{"field": "nonexistent", "op": "eq", "value": 1}]})


def test_unknown_filter_op_rejected():
    table = build_table(_module())
    with pytest.raises(ReportError):
        _validate_definition(table, {"group_by": [], "measures": [], "filters": [{"field": "amount", "op": "like", "value": 1}]})
