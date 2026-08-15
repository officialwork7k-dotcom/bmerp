"""Fiscal-period gate: blocks create/update/delete on a record whose
period-gate date field (see FieldMetadata.is_period_gate) falls inside a
CLOSED fiscal_periods row for the acting client. One calendar-month period
per client, period_key "YYYY-MM" — no separate fiscal-year-start-month
config; a real close-the-books workflow can still be modeled as one
metadata-driven module authored in Part 2 if a non-calendar fiscal year is
ever needed, this just gates the framework-level mechanics.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.metadata import ModuleMetadata
from metaforge_api.infrastructure.models import FiscalPeriod


class PeriodClosedError(Exception):
    def __init__(self, period_key: str):
        self.period_key = period_key
        super().__init__(f"fiscal period {period_key} is closed for posting")


def period_key_for(value: Any) -> str | None:
    """"YYYY-MM" for a date/datetime/ISO-string value; None if the field is
    empty (an unset period-gate date simply isn't gated — same "no
    constraint until there's a value" stance as everything else here)."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value[:10]
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return f"{value.year:04d}-{value.month:02d}"
    return None


async def check(session: AsyncSession, module: ModuleMetadata, client_code: str | None, row: dict[str, Any]) -> None:
    """Raises PeriodClosedError if `row`'s period-gate field falls inside a
    closed period for `client_code`. A no-op if the module has no
    period-gate field, the field is unset, or client_code is None (the rare
    framework-internal caller that bypasses tenancy entirely — see
    DataRepository.__init__)."""
    if client_code is None:
        return
    field = module.period_gate_field()
    if field is None:
        return
    period_key = period_key_for(row.get(field.name))
    if period_key is None:
        return
    period = (
        await session.execute(
            select(FiscalPeriod).where(FiscalPeriod.client_code == client_code, FiscalPeriod.period_key == period_key)
        )
    ).scalar_one_or_none()
    if period is not None and period.status == "closed":
        raise PeriodClosedError(period_key)
