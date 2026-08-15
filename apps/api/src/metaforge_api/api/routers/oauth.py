"""Google OAuth/OIDC login — a second way to authenticate onto the exact
same session mechanism auth.py's password login uses (same JWT/cookie/
Valkey-session issuance), so get_current_user and everything downstream
of it needs zero changes.

`state` is a short-lived signed JWT (not server-side storage) — it only
needs to prove "this callback belongs to a /start we actually issued a
few seconds ago," which a signature+expiry check does without needing
Valkey/DB round trips or cleanup.

Resolution ladder at the callback, in order:
1. (provider, subject) already linked to a User -> normal login.
2. No identity, but the verified email matches this user's own existing
   account by username -> not supported in v1 (see provisioning.py's
   docstring); every new (provider, subject) either matches a prior OAuth
   login or provisions a brand-new org. Linking Google onto an existing
   password account is a deliberately deferred "logged-in link" flow, not
   done implicitly here — implicit email-matching to an EXISTING account
   is exactly the account-takeover shape this file avoids (see point 3).
3. No identity at all -> self-service provisioning (provisioning.py):
   brand-new Client + User seeded as that org's Org Admin + starter data.

Google's `email_verified` claim is required before the email is trusted
for anything (matches this file's own account, or is used as the new
org's display seed) — an unverified email is never sufficient grounds to
attach to an existing identity or org.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from metaforge_api.api.deps import DbSession
from metaforge_api.api.routers.auth import _COOKIE_NAME, _TOKEN_TTL, _issue_token
from metaforge_api.infrastructure import cache, provisioning
from metaforge_api.infrastructure.models import OauthIdentity, User
from metaforge_api.infrastructure.settings import settings

router = APIRouter(prefix="/api/auth/oauth", tags=["oauth"])

_STATE_TTL = timedelta(minutes=10)
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret and settings.public_base_url)


def _redirect_uri() -> str:
    return f"{settings.public_base_url}/api/auth/oauth/google/callback"


def _make_state() -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"nonce": secrets.token_urlsafe(8), "iat": now, "exp": now + _STATE_TTL},
        settings.session_secret,
        algorithm="HS256",
    )


def _verify_state(state: str) -> None:
    try:
        jwt.decode(state, settings.session_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(400, "invalid or expired oauth state") from None


@router.get("/google/start")
async def google_start():
    if not _configured():
        raise HTTPException(503, "Google sign-in is not configured on this instance")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": _make_state(),
        "prompt": "select_account",
    }
    return RedirectResponse(f"{_GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(code: str, state: str, session: DbSession):
    if not _configured():
        raise HTTPException(503, "Google sign-in is not configured on this instance")
    _verify_state(state)

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(502, "Google token exchange failed")
        access_token = token_resp.json()["access_token"]

        userinfo_resp = await client.get(_GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        if userinfo_resp.status_code != 200:
            raise HTTPException(502, "Google userinfo request failed")
        info = userinfo_resp.json()

    subject = info["sub"]
    email = (info.get("email") or "").lower()
    email_verified = bool(info.get("email_verified"))
    name = info.get("name") or email or "New User"

    identity = (
        await session.execute(
            select(OauthIdentity).where(OauthIdentity.provider == "google", OauthIdentity.subject == subject)
        )
    ).scalar_one_or_none()

    if identity is not None:
        user = (await session.execute(select(User).where(User.id == identity.user_id))).scalar_one()
        identity.last_login_at = datetime.now(timezone.utc)
    else:
        if not email_verified:
            raise HTTPException(403, "Google account email is not verified — cannot create an account from it")
        user = await provisioning.provision_org(session, email=email, display_name=name)
        identity = OauthIdentity(
            user_id=user.id, provider="google", subject=subject, email=email, email_verified=email_verified,
            last_login_at=datetime.now(timezone.utc),
        )
        session.add(identity)

    if not user.is_active:
        raise HTTPException(403, "account disabled")

    await session.commit()

    client_code = user.default_client_code
    session_id = uuid.uuid4().hex
    await cache.set_session(session_id, str(user.id))
    token = _issue_token(str(user.id), session_id, client_code)

    response = RedirectResponse(settings.public_base_url or "/")
    response.set_cookie(
        _COOKIE_NAME, token, httponly=True, samesite="lax", secure=True, max_age=int(_TOKEN_TTL.total_seconds())
    )
    return response
