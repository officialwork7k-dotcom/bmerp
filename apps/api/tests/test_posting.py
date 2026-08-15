from datetime import date, datetime
from decimal import Decimal

import pytest

from metaforge_api.infrastructure.posting import PostingError, _header_line, _resolve_posting_date, _to_decimal


def test_to_decimal_handles_none_and_empty():
    assert _to_decimal(None) == Decimal("0")
    assert _to_decimal("") == Decimal("0")
    assert _to_decimal("12.50") == Decimal("12.50")
    assert _to_decimal(5) == Decimal("5")


def test_header_line_debit_side():
    rule = {"account_code": "1000", "account_name": "Cash", "amount_formula": "qty * unit_price", "side": "debit"}
    line = _header_line(rule, {"qty": 3, "unit_price": 10})
    assert line.account_code == "1000"
    assert line.debit == Decimal("30")
    assert line.credit == Decimal("0")


def test_header_line_credit_side():
    rule = {"account_code": "2000", "amount_formula": "amount", "side": "credit"}
    line = _header_line(rule, {"amount": 100})
    assert line.credit == Decimal("100")
    assert line.debit == Decimal("0")


def test_header_line_rejects_negative_amount():
    rule = {"account_code": "1000", "amount_formula": "amount", "side": "debit"}
    with pytest.raises(PostingError):
        _header_line(rule, {"amount": -5})


def test_header_line_rejects_invalid_side():
    rule = {"account_code": "1000", "amount_formula": "amount", "side": "sideways"}
    with pytest.raises(PostingError):
        _header_line(rule, {"amount": 5})


def test_resolve_posting_date_from_date_field():
    rules = {"date_field": "invoice_date"}
    assert _resolve_posting_date(rules, {"invoice_date": date(2026, 8, 13)}) == date(2026, 8, 13)


def test_resolve_posting_date_from_datetime_value():
    rules = {"date_field": "invoice_date"}
    assert _resolve_posting_date(rules, {"invoice_date": datetime(2026, 8, 13, 10, 30)}) == date(2026, 8, 13)


def test_resolve_posting_date_from_iso_string():
    rules = {"date_field": "invoice_date"}
    assert _resolve_posting_date(rules, {"invoice_date": "2026-08-13"}) == date(2026, 8, 13)


def test_resolve_posting_date_falls_back_to_today_when_unset():
    rules = {"date_field": "invoice_date"}
    result = _resolve_posting_date(rules, {})
    assert isinstance(result, date)
