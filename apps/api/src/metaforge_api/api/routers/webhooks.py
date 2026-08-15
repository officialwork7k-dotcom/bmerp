from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select

from metaforge_api.api.deps import AdminUser, DbSession
from metaforge_api.infrastructure.models import Webhook

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class WebhookIn(BaseModel):
    module: str
    url: str
    events: list[str] = ["create", "update", "delete"]
    is_active: bool = True


def _out(w: Webhook, *, with_secret: bool = False) -> dict:
    d = {"id": str(w.id), "module": w.module, "url": w.url, "events": w.events, "is_active": w.is_active}
    if with_secret:
        d["secret"] = w.secret
    return d


@router.get("")
async def list_webhooks(session: DbSession, user: AdminUser):
    rows = (
        await session.execute(
            select(Webhook).where(or_(Webhook.client_code == user.client_code, Webhook.client_code.is_(None)))
        )
    ).scalars().all()
    return [_out(w) for w in rows]


@router.post("")
async def create_webhook(body: WebhookIn, session: DbSession, user: AdminUser):
    webhook = Webhook(
        module=body.module,
        client_code=user.client_code,
        url=body.url,
        events=body.events,
        is_active=body.is_active,
        secret=secrets.token_hex(32),
    )
    session.add(webhook)
    await session.commit()
    # Secret is only ever shown once, at creation — same pattern as an API
    # token — so the receiver's verification setup has something to copy,
    # but a later GET can't leak it.
    return _out(webhook, with_secret=True)


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: uuid.UUID, session: DbSession, user: AdminUser):
    row = (await session.execute(select(Webhook).where(Webhook.id == webhook_id))).scalar_one_or_none()
    if row is None:
        return
    if row.client_code is not None and row.client_code != user.client_code:
        raise HTTPException(403, "not your webhook")
    await session.delete(row)
    await session.commit()
