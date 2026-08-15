"""In-app notification center — bell-icon backing store. Polled by the
frontend rather than pushed (no websocket infra at this scale); cheap
enough at typical per-user volumes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import or_, select, update

from metaforge_api.api.deps import CurrentUser, CurrentUserDep, DbSession
from metaforge_api.infrastructure.models import Notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _client_scope(query, user: CurrentUser):
    # NULL client_code means either a pre-migration row or a notification
    # with no record link (e.g. none currently, but the column allows it) —
    # always visible, same convention `client_code IS NULL` uses everywhere
    # else in this framework for "applies globally."
    if user.client_code is not None:
        query = query.where(or_(Notification.client_code == user.client_code, Notification.client_code.is_(None)))
    return query


@router.get("")
async def list_notifications(session: DbSession, user: CurrentUserDep, limit: int = 50):
    rows = (
        await session.execute(
            _client_scope(select(Notification), user)
            .where(Notification.user_id == uuid.UUID(user.id))
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "body": n.body,
            "link": n.link,
            "read": n.read_at is not None,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.get("/unread-count")
async def unread_count(session: DbSession, user: CurrentUserDep):
    from sqlalchemy import func

    count = (
        await session.execute(
            _client_scope(select(func.count()).select_from(Notification), user)
            .where(Notification.user_id == uuid.UUID(user.id), Notification.read_at.is_(None))
        )
    ).scalar_one()
    return {"count": count}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    await session.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == uuid.UUID(user.id))
        .values(read_at=datetime.now(timezone.utc))
    )
    await session.commit()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(session: DbSession, user: CurrentUserDep):
    await session.execute(
        update(Notification)
        .where(Notification.user_id == uuid.UUID(user.id), Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await session.commit()
    return {"ok": True}
