"""Minimal report engine API — see infrastructure/reports.py."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUserDep, DbSession, Registry
from metaforge_api.infrastructure import reports
from metaforge_api.infrastructure.models import Report

router = APIRouter(prefix="/api/reports", tags=["reports"])


class MeasureIn(BaseModel):
    field: str | None = None
    op: str
    label: str | None = None


class FilterIn(BaseModel):
    field: str
    op: str
    value: Any


class DefinitionIn(BaseModel):
    source_module: str
    group_by: list[str] = []
    measures: list[MeasureIn] = []
    filters: list[FilterIn] = []


class ReportIn(BaseModel):
    name: str
    definition: DefinitionIn


def _report_out(r: Report) -> dict:
    return {"id": str(r.id), "name": r.name, "definition": r.definition, "created_at": r.created_at.isoformat()}


@router.get("")
async def list_reports(session: DbSession, user: CurrentUserDep):
    rows = (
        await session.execute(select(Report).where(Report.client_code == user.client_code).order_by(Report.created_at.desc()))
    ).scalars().all()
    return [_report_out(r) for r in rows]


@router.post("")
async def create_report(body: ReportIn, session: DbSession, user: CurrentUserDep):
    report = Report(
        client_code=user.client_code, name=body.name, definition=body.definition.model_dump(), created_by=uuid.UUID(user.id)
    )
    session.add(report)
    await session.commit()
    return _report_out(report)


@router.get("/{report_id}")
async def get_report(report_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    row = (
        await session.execute(select(Report).where(Report.id == report_id, Report.client_code == user.client_code))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "report not found")
    return _report_out(row)


@router.put("/{report_id}")
async def update_report(report_id: uuid.UUID, body: ReportIn, session: DbSession, user: CurrentUserDep):
    row = (
        await session.execute(select(Report).where(Report.id == report_id, Report.client_code == user.client_code))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "report not found")
    row.name = body.name
    row.definition = body.definition.model_dump()
    await session.commit()
    return _report_out(row)


@router.delete("/{report_id}", status_code=204)
async def delete_report(report_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    row = (
        await session.execute(select(Report).where(Report.id == report_id, Report.client_code == user.client_code))
    ).scalar_one_or_none()
    if row is not None:
        await session.delete(row)
        await session.commit()


@router.post("/run")
async def run_ad_hoc(body: DefinitionIn, session: DbSession, registry: Registry, user: CurrentUserDep):
    try:
        return await reports.run_report(session, registry, body.model_dump(), client_code=user.client_code)
    except (reports.ReportError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from None


@router.get("/{report_id}/run")
async def run_saved(report_id: uuid.UUID, session: DbSession, registry: Registry, user: CurrentUserDep):
    row = (
        await session.execute(select(Report).where(Report.id == report_id, Report.client_code == user.client_code))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "report not found")
    try:
        return await reports.run_report(session, registry, row.definition, client_code=user.client_code)
    except (reports.ReportError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from None
