"""Username/password auth with a rotated JWT in an httponly cookie.

The JWT carries a `jti` (session id) that's also stored in Valkey mapped to
the user id — this makes the token revocable on logout (a bare JWT can't be
invalidated server-side before its `exp`), per the required stack's "Cache:
Valkey ... session fragments".
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUserDep, DbSession, _resolve_client_code, merge_roles
from metaforge_api.infrastructure import cache
from metaforge_api.infrastructure.models import User
from metaforge_api.infrastructure.settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")
_COOKIE_NAME = "mf_session"
_TOKEN_TTL = timedelta(hours=8)
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT = timedelta(minutes=15)


class LoginIn(BaseModel):
    username: str
    password: str
    # Only needed when a user is assigned to more than one client and has no
    # default set — _resolve_client_code raises a 400 telling the frontend
    # to prompt for this rather than guessing.
    client_code: str | None = None


def _issue_token(user_id: str, session_id: str, client_code: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user_id, "jti": session_id, "iat": now, "exp": now + _TOKEN_TTL, "client_code": client_code},
        settings.session_secret,
        algorithm="HS256",
    )


@router.post("/login")
async def login(body: LoginIn, response: Response, session: DbSession):
    user = (await session.execute(select(User).where(User.username == body.username))).scalar_one_or_none()

    # Deliberately checked even when the user doesn't exist, with the same
    # "invalid credentials" message either way — a distinct "no such user"
    # response is a username-enumeration oracle.
    now = datetime.now(timezone.utc)
    if user is not None and user.locked_until is not None and user.locked_until > now:
        raise HTTPException(429, "account temporarily locked; try again later")

    # An OAuth-only user (see OauthIdentity) has no password_hash — reject
    # explicitly rather than handing passlib a None hash, which raises
    # instead of just returning False.
    valid = (
        user is not None and user.is_active and user.password_hash is not None
        and _pwd.verify(body.password, user.password_hash)
    )
    if not valid:
        if user is not None:
            user.failed_login_count += 1
            if user.failed_login_count >= _MAX_FAILED_ATTEMPTS:
                user.locked_until = now + _LOCKOUT
                user.failed_login_count = 0
            await session.commit()
        raise HTTPException(401, "invalid credentials")

    user.failed_login_count = 0
    user.locked_until = None
    await session.commit()

    # Raises 403 (not assigned to the requested client) or 400 (ambiguous —
    # multiple clients, no default, none requested) before any session is
    # issued, per _resolve_client_code's contract.
    client_code = _resolve_client_code(user, body.client_code)

    session_id = uuid.uuid4().hex
    await cache.set_session(session_id, str(user.id))
    token = _issue_token(str(user.id), session_id, client_code)
    response.set_cookie(
        _COOKIE_NAME, token, httponly=True, samesite="lax", secure=True, max_age=int(_TOKEN_TTL.total_seconds())
    )

    is_admin, module_permissions = merge_roles(user.roles)
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": is_admin,
        "module_permissions": module_permissions,
        "theme": user.theme,
        "client_code": client_code,
        "available_clients": sorted(c.code for c in user.clients),
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(_COOKIE_NAME)
    if token:
        try:
            payload = jwt.decode(token, settings.session_secret, algorithms=["HS256"])
            await cache.revoke_session(payload["jti"])
        except jwt.PyJWTError:
            pass
    response.delete_cookie(_COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
async def me(user: CurrentUserDep, session: DbSession):
    row = (await session.execute(select(User).where(User.id == uuid.UUID(user.id)))).scalar_one_or_none()
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "module_permissions": user.module_permissions,
        "theme": user.theme,
        "client_code": user.client_code,
        "available_clients": sorted(c.code for c in row.clients) if row else [user.client_code],
    }


class SwitchClientIn(BaseModel):
    client_code: str


@router.post("/switch-client")
async def switch_client(body: SwitchClientIn, request: Request, response: Response, session: DbSession, user: CurrentUserDep):
    """Re-issues the session cookie for a different client this user is
    already assigned to — no password re-entry, since they're already
    authenticated; this is a self-service pick among orgs an admin already
    granted them, not a privilege change. The old session's `jti` is
    revoked and a fresh one issued (rather than mutating the existing
    token's claims) so a stolen pre-switch token can't be replayed after
    the switch."""
    row = (await session.execute(select(User).where(User.id == uuid.UUID(user.id)))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "user not found")
    client_code = _resolve_client_code(row, body.client_code)

    token = request.cookies.get(_COOKIE_NAME)
    if token:
        try:
            payload = jwt.decode(token, settings.session_secret, algorithms=["HS256"])
            await cache.revoke_session(payload["jti"])
        except jwt.PyJWTError:
            pass

    session_id = uuid.uuid4().hex
    await cache.set_session(session_id, str(row.id))
    new_token = _issue_token(str(row.id), session_id, client_code)
    response.set_cookie(
        _COOKIE_NAME, new_token, httponly=True, samesite="lax", secure=True, max_age=int(_TOKEN_TTL.total_seconds())
    )

    is_admin, module_permissions = merge_roles(row.roles)
    return {
        "id": str(row.id),
        "username": row.username,
        "display_name": row.display_name,
        "is_admin": is_admin,
        "module_permissions": module_permissions,
        "theme": row.theme,
        "client_code": client_code,
        "available_clients": sorted(c.code for c in row.clients),
    }


class ThemeIn(BaseModel):
    theme: str


@router.put("/theme")
async def set_theme(body: ThemeIn, session: DbSession, user: CurrentUserDep):
    """Self-service — any signed-in user sets their own theme, no admin
    role required (unlike /admin/users, which edits *other* people's
    accounts). Kept in the auth router rather than admin.py for that
    reason: this is "my own preference," not user administration."""
    row = (await session.execute(select(User).where(User.id == user.id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "user not found")
    row.theme = body.theme
    await session.commit()
    return {"theme": row.theme}
