"""Read-only surface over the posting engine's output (see
infrastructure/posting.py) — not a Builder module, same reasoning as
Users/Roles: journal_entries/journal_lines are engine-owned, append-only
tables, not metadata-driven business objects. A reversal is triggered here
too, since "reverse this entry" is an action on the engine's own data, not
on a document module.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUserDep, DbSession, Registry
from metaforge_api.infrastructure import posting
from metaforge_api.infrastructure.models import JournalEntry, JournalLine

router = APIRouter(prefix="/api/gl", tags=["gl"])


def _entry_out(e: JournalEntry) -> dict:
    return {
        "id": str(e.id),
        "client_code": e.client_code,
        "document_module": e.document_module,
        "document_id": str(e.document_id),
        "posting_date": e.posting_date.isoformat(),
        "description": e.description,
        "status": e.status,
        "reversal_of": str(e.reversal_of) if e.reversal_of else None,
        "posted_at": e.posted_at.isoformat(),
    }


def _line_out(l: JournalLine) -> dict:
    return {
        "id": str(l.id),
        "line_no": l.line_no,
        "account_code": l.account_code,
        "account_name": l.account_name,
        "debit": float(l.debit),
        "credit": float(l.credit),
    }


@router.get("/journal-entries")
async def list_journal_entries(
    session: DbSession, user: CurrentUserDep,
    document_module: str | None = None, document_id: uuid.UUID | None = None, limit: int = 50,
):
    query = select(JournalEntry).where(JournalEntry.client_code == user.client_code)
    if document_module:
        query = query.where(JournalEntry.document_module == document_module)
    if document_id:
        query = query.where(JournalEntry.document_id == document_id)
    query = query.order_by(JournalEntry.posted_at.desc()).limit(min(limit, 200))
    rows = (await session.execute(query)).scalars().all()
    return [_entry_out(e) for e in rows]


@router.get("/journal-entries/{entry_id}")
async def get_journal_entry(entry_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    entry = (
        await session.execute(
            select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.client_code == user.client_code)
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(404, "journal entry not found")
    lines = (
        await session.execute(select(JournalLine).where(JournalLine.journal_entry_id == entry_id).order_by(JournalLine.line_no))
    ).scalars().all()
    return {**_entry_out(entry), "lines": [_line_out(l) for l in lines]}


@router.post("/backfill/{module}")
async def backfill_postings(module: str, session: DbSession, registry: Registry, user: CurrentUserDep):
    """GL hygiene tool: posts a journal entry for any record already sitting
    in its trigger_status with none — the known gap when posting_rules is
    added to a module after some documents already reached that status
    under the old (rule-less) metadata. Admin-only since it writes journal
    entries outside the normal document-transition flow."""
    if not user.is_admin:
        raise HTTPException(403, "admin only")
    try:
        created = await posting.backfill_missing_postings(
            session, registry, module, client_code=user.client_code, actor_id=uuid.UUID(user.id)
        )
    except posting.PostingError as exc:
        raise HTTPException(409, str(exc)) from None
    await session.commit()
    return {"created": len(created), "journal_entry_ids": [str(e.id) for e in created]}


@router.post("/journal-entries/{entry_id}/reverse")
async def reverse_journal_entry(entry_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    entry = (
        await session.execute(
            select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.client_code == user.client_code)
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(404, "journal entry not found")
    try:
        reversal = await posting.reverse(session, entry_id, actor_id=uuid.UUID(user.id))
    except posting.PostingError as exc:
        raise HTTPException(409, str(exc)) from None
    await session.commit()
    return _entry_out(reversal)
