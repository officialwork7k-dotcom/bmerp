import pytest

from metaforge_api.domain.formulas import FormulaError, evaluate_formula


def test_basic_arithmetic():
    assert evaluate_formula("qty * unit_price", {"qty": 3, "unit_price": 10}) == 30


def test_division_by_zero_returns_zero_not_exception():
    assert evaluate_formula("total / qty", {"total": 100, "qty": 0}) == 0.0


def test_missing_field_defaults_to_zero():
    assert evaluate_formula("qty * unit_price", {"qty": 3}) == 0


def test_rejects_non_arithmetic_expressions():
    with pytest.raises(FormulaError):
        evaluate_formula("__import__('os').system('echo pwned')", {})


def test_comparison_returns_bool():
    assert evaluate_formula("balance > 0", {"balance": 5}) is True
    assert evaluate_formula("balance > 0", {"balance": -5}) is False


def test_chained_comparison():
    assert evaluate_formula("0 < qty < 10", {"qty": 5}) is True
    assert evaluate_formula("0 < qty < 10", {"qty": 15}) is False


def test_boolean_and_or_not():
    assert evaluate_formula("qty > 0 and price > 0", {"qty": 1, "price": 1}) is True
    assert evaluate_formula("qty > 0 and price > 0", {"qty": 1, "price": 0}) is False
    assert evaluate_formula("qty > 0 or price > 0", {"qty": 0, "price": 1}) is True
    assert evaluate_formula("not is_closed", {"is_closed": 0}) is True


def test_ternary_conditional():
    assert evaluate_formula("price * 0.9 if qty > 10 else price", {"qty": 20, "price": 100}) == 90
    assert evaluate_formula("price * 0.9 if qty > 10 else price", {"qty": 5, "price": 100}) == 100


def test_round_abs_min_max_functions():
    assert evaluate_formula("ROUND(amount, 2)", {"amount": 1.005}) == round(1.005, 2)
    assert evaluate_formula("ROUND(amount)", {"amount": 4.6}) == 5
    assert evaluate_formula("ABS(delta)", {"delta": -3}) == 3
    assert evaluate_formula("MIN(a, b)", {"a": 3, "b": 7}) == 3
    assert evaluate_formula("MAX(a, b)", {"a": 3, "b": 7}) == 7


def test_rejects_unknown_function():
    with pytest.raises(FormulaError):
        evaluate_formula("SUM(a, b)", {"a": 1, "b": 2})


def test_rejects_keyword_arguments():
    with pytest.raises(FormulaError):
        evaluate_formula("ROUND(amount, ndigits=2)", {"amount": 1.005})
