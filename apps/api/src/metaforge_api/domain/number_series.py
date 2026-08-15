"""Pure logic for AUTO_NUMBER counters — no DB/framework imports, shared
between the allocation path (infrastructure/repository.py) and the admin
config API (api/routers/number_series.py) so both compute the exact same
period key for a given reset_policy."""

from __future__ import annotations

from datetime import datetime, timezone


def current_period_key(reset_policy: str) -> str:
    now = datetime.now(timezone.utc)
    # "fiscal_year" resets on the same boundary as "yearly" — this
    # framework's fiscal year is the calendar year (see infrastructure/
    # fiscal.py's one-calendar-month-period model). Kept as a distinct
    # declared policy rather than aliased away so a future non-calendar
    # fiscal year only has to change this one branch, and so the Builder UI
    # can offer it as "resets each fiscal year" without lying about what it
    # does today.
    if reset_policy in ("yearly", "fiscal_year"):
        return str(now.year)
    if reset_policy == "monthly":
        return f"{now.year}-{now.month:02d}"
    return ""
