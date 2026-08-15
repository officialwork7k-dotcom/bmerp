from decimal import Decimal

from metaforge_api.infrastructure.depreciation import _to_decimal, run_depreciation
from metaforge_api.infrastructure.periodic_runs import _REGISTRY


def test_to_decimal_handles_none_and_empty():
    assert _to_decimal(None) == Decimal("0")
    assert _to_decimal("") == Decimal("0")
    assert _to_decimal("10.5") == Decimal("10.5")


def test_importing_depreciation_registers_asset_depreciation_run():
    assert _REGISTRY["asset_depreciation"] is run_depreciation


def test_straight_line_monthly_amount():
    cost, salvage, life = Decimal("12000"), Decimal("0"), 24
    monthly = (cost - salvage) / life
    assert monthly == Decimal("500")


def test_depreciation_capped_at_remaining_base():
    depreciable_base = Decimal("1000")
    accumulated = Decimal("900")
    monthly = Decimal("500")
    remaining = depreciable_base - accumulated
    amount = min(monthly, remaining)
    assert amount == Decimal("100")
