from metaforge_api.domain.metadata import FieldDataType, FieldMetadata, ModuleMetadata
from metaforge_api.infrastructure.repository import apply_formulas


def _field(name, dtype, formula=None):
    return FieldMetadata(name=name, label=name, data_type=dtype, control_type="", formula=formula)


MODULE = ModuleMetadata(
    name="purchase_order_lines",
    label="PO Lines",
    fields=(
        _field("qty", FieldDataType.INTEGER),
        _field("unit_price", FieldDataType.MONEY),
        _field("line_total", FieldDataType.MONEY, formula="qty * unit_price"),
    ),
)


def test_formula_field_is_computed_from_sibling_fields():
    out = apply_formulas(MODULE, {"qty": 20, "unit_price": 145.0})
    assert out["line_total"] == 2900.0


def test_computed_value_overrides_whatever_client_sent():
    out = apply_formulas(MODULE, {"qty": 2, "unit_price": 10, "line_total": 999999})
    assert out["line_total"] == 20.0
