"""Financial statement reports API — trial balance, AR/AP aging,
vendor/customer ledgers. See infrastructure/financial_reports.py."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, HTTPException

from metaforge_api.api.deps import CurrentUserDep, DbSession, Registry
from metaforge_api.infrastructure import financial_reports

router = APIRouter(prefix="/api/financial-reports", tags=["financial-reports"])

_VALID_GROUPS = {"AP", "AR"}


def _check_group(group: str) -> None:
    if group not in _VALID_GROUPS:
        raise HTTPException(400, f"group must be one of {sorted(_VALID_GROUPS)}")


@router.get("/trial-balance")
async def trial_balance(session: DbSession, registry: Registry, user: CurrentUserDep, as_of_date: date):
    return await financial_reports.trial_balance(session, registry, client_code=user.client_code, as_of_date=as_of_date)


@router.get("/balance-sheet")
async def balance_sheet(session: DbSession, registry: Registry, user: CurrentUserDep, as_of_date: date):
    return await financial_reports.balance_sheet(session, registry, client_code=user.client_code, as_of_date=as_of_date)


@router.get("/income-statement")
async def income_statement(session: DbSession, registry: Registry, user: CurrentUserDep, date_from: date, date_to: date):
    return await financial_reports.income_statement(session, registry, client_code=user.client_code, date_from=date_from, date_to=date_to)


@router.get("/aging")
async def aging(session: DbSession, registry: Registry, user: CurrentUserDep, group: str, as_of_date: date):
    _check_group(group)
    try:
        return await financial_reports.aging_report(session, registry, client_code=user.client_code, group=group, as_of_date=as_of_date)
    except financial_reports.ReportError as exc:
        raise HTTPException(400, str(exc)) from None


@router.get("/subledger-reconciliation")
async def subledger_reconciliation(session: DbSession, registry: Registry, user: CurrentUserDep, as_of_date: date):
    return await financial_reports.subledger_reconciliation(session, registry, client_code=user.client_code, as_of_date=as_of_date)


@router.get("/ledger")
async def ledger(
    session: DbSession, registry: Registry, user: CurrentUserDep,
    group: str, party_id: uuid.UUID, date_from: date, date_to: date,
):
    _check_group(group)
    try:
        return await financial_reports.party_ledger(
            session, registry, client_code=user.client_code, group=group, party_id=party_id, date_from=date_from, date_to=date_to
        )
    except financial_reports.ReportError as exc:
        raise HTTPException(400, str(exc)) from None
