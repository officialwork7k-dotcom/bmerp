from decimal import Decimal

from metaforge_api.infrastructure.clearing import _to_decimal


def test_to_decimal_handles_none_and_empty():
    assert _to_decimal(None) == Decimal("0")
    assert _to_decimal("") == Decimal("0")


def test_to_decimal_parses_numeric_values():
    assert _to_decimal("42.50") == Decimal("42.50")
    assert _to_decimal(10) == Decimal("10")


def test_net_zero_within_tolerance():
    from metaforge_api.infrastructure.clearing import _TOLERANCE

    amounts = [Decimal("100.00"), Decimal("-99.995")]
    assert abs(sum(amounts, Decimal("0"))) <= _TOLERANCE


def test_net_nonzero_exceeds_tolerance():
    from metaforge_api.infrastructure.clearing import _TOLERANCE

    amounts = [Decimal("100.00"), Decimal("-90.00")]
    assert abs(sum(amounts, Decimal("0"))) > _TOLERANCE
