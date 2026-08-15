from decimal import Decimal

from metaforge_api.infrastructure.stock import _to_decimal


def test_to_decimal_handles_none_and_empty():
    assert _to_decimal(None) == Decimal("0")
    assert _to_decimal("") == Decimal("0")


def test_to_decimal_parses_numeric_values():
    assert _to_decimal("12.5") == Decimal("12.5")
    assert _to_decimal(7) == Decimal("7")


def test_weighted_moving_average_formula():
    # 10 units @ $2 on hand, receive 10 more @ $4 -> new avg should be $3
    on_hand, avg_cost = Decimal("10"), Decimal("2")
    qty, unit_cost = Decimal("10"), Decimal("4")
    new_qty = on_hand + qty
    new_avg = (on_hand * avg_cost + qty * unit_cost) / new_qty
    assert new_qty == Decimal("20")
    assert new_avg == Decimal("3")
