from datetime import datetime, timezone

from metaforge_api.domain.number_series import current_period_key


def test_never_resets_to_empty_key():
    assert current_period_key("never") == ""


def test_yearly_and_fiscal_year_share_the_same_boundary():
    year = str(datetime.now(timezone.utc).year)
    assert current_period_key("yearly") == year
    assert current_period_key("fiscal_year") == year


def test_monthly_key_format():
    now = datetime.now(timezone.utc)
    assert current_period_key("monthly") == f"{now.year}-{now.month:02d}"
