from datetime import date, datetime

from metaforge_api.infrastructure.fiscal import period_key_for


def test_period_key_for_date():
    assert period_key_for(date(2026, 8, 13)) == "2026-08"


def test_period_key_for_datetime():
    assert period_key_for(datetime(2026, 1, 5, 10, 30)) == "2026-01"


def test_period_key_for_iso_string():
    assert period_key_for("2026-12-31") == "2026-12"


def test_period_key_for_iso_datetime_string():
    assert period_key_for("2026-03-15T00:00:00+00:00") == "2026-03"


def test_period_key_for_none_or_empty():
    assert period_key_for(None) is None
    assert period_key_for("") is None


def test_period_key_for_garbage_string():
    assert period_key_for("not-a-date") is None
