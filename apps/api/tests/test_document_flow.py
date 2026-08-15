from decimal import Decimal

import pytest

from metaforge_api.domain.metadata import FieldDataType, FieldMetadata, ModuleMetadata
from metaforge_api.infrastructure.document_flow import DocumentFlowError, _find_flow, _to_decimal


def _module_with_flows(flows):
    return ModuleMetadata(name="purchase_orders", label="POs", fields=(), document_flows=flows)


def test_to_decimal_handles_none_and_empty():
    assert _to_decimal(None) == Decimal("0")
    assert _to_decimal("") == Decimal("0")
    assert _to_decimal("3.5") == Decimal("3.5")


def test_find_flow_returns_matching_definition():
    flows = [{"name": "PO to GR", "target_module": "goods_receipts"}]
    module = _module_with_flows(flows)
    assert _find_flow(module, "PO to GR") == flows[0]


def test_find_flow_raises_for_unknown_name():
    module = _module_with_flows([{"name": "PO to GR", "target_module": "goods_receipts"}])
    with pytest.raises(DocumentFlowError):
        _find_flow(module, "does not exist")


def test_find_flow_raises_when_no_flows_defined():
    module = _module_with_flows(None)
    with pytest.raises(DocumentFlowError):
        _find_flow(module, "anything")


def test_tolerance_math():
    remaining = Decimal("10")
    tolerance_pct = Decimal("5") / Decimal("100")
    max_allowed = remaining * (1 + tolerance_pct)
    assert max_allowed == Decimal("10.50")
