"""Scoped personal-access tokens for integrations — created once, shown
once (plain value never stored, never retrievable again), then used as a
`Bearer` token in place of the cookie session for machine callers."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUserDep, DbSession
from metaforge_api.infrastructure.models import ApiToken

router = APIRouter(prefix="/api/tokens", tags=["tokens"])
_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


class TokenIn(BaseModel):
    name: str


@router.get("")
async def list_tokens(session: DbSession, user: CurrentUserDep):
    rows = (
        await session.execute(select(ApiToken).where(ApiToken.user_id == uuid.UUID(user.id), ApiToken.revoked.is_(False)))
    ).scalars().all()
    return [
        {"id": str(t.id), "name": t.name, "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None}
        for t in rows
    ]


@router.post("")
async def create_token(body: TokenIn, session: DbSession, user: CurrentUserDep):
    raw = f"mf_{secrets.token_urlsafe(32)}"
    token = ApiToken(user_id=uuid.UUID(user.id), name=body.name, token_hash=_pwd.hash(raw))
    session.add(token)
    await session.commit()
    return {"id": str(token.id), "name": token.name, "token": raw}


@router.delete("/{token_id}", status_code=204)
async def revoke_token(token_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    row = (await session.execute(select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == uuid.UUID(user.id)))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "token not found")
    row.revoked = True
    await session.commit()
