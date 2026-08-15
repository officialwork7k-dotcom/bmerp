from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.infrastructure import cache
from metaforge_api.infrastructure.db import get_session
from metaforge_api.infrastructure.models import ApiToken, Role, User
from metaforge_api.infrastructure.module_registry import SessionModuleRegistry
from metaforge_api.infrastructure.repository import DataRepository
from metaforge_api.infrastructure.settings import settings


def merge_roles(roles: list[Role]) -> tuple[bool, dict]:
    """A user can hold several small roles at once — effective access is
    the union, not any single role's own permissions: is_admin if ANY
    assigned role is_admin, and per-module-per-action OR across every
    role's module_permissions (one role granting an action is enough, even
    if another assigned role doesn't mention that module/action at all)."""
    is_admin = any(r.is_admin for r in roles)
    merged: dict[str, dict[str, bool]] = {}
    for role in roles:
        for module_name, actions in role.module_permissions.items():
            entry = merged.setdefault(module_name, {})
            for action, allowed in actions.items():
                if allowed:
                    entry[action] = True
    return is_admin, merged

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")

DbSession = Annotated[AsyncSession, Depends(get_session)]

_COOKIE_NAME = "mf_session"


async def get_registry(session: DbSession) -> SessionModuleRegistry:
    registry = SessionModuleRegistry()
    await registry.load_all(session)
    return registry


Registry = Annotated[SessionModuleRegistry, Depends(get_registry)]


@dataclass
class CurrentUser:
    id: str
    username: str
    display_name: str
    is_admin: bool
    module_permissions: dict
    theme: str
    # Active SAP-MANDT-style tenant for this session — see repository.py's
    # client_code scoping. Every dynamic-module read/write goes through it.
    client_code: str


def _resolve_client_code(user: User, requested: str | None) -> str:
    """Picks the active client for a login/token: the requested code if the
    user is actually assigned to it, else their configured default, else
    (for a single-client user) their only assignment. Raises if none of
    those resolve — a user with zero client assignments cannot sign in."""
    assigned = {c.code for c in user.clients}
    if requested is not None:
        if requested not in assigned:
            raise HTTPException(403, f"not assigned to client '{requested}'")
        return requested
    if user.default_client_code and user.default_client_code in assigned:
        return user.default_client_code
    if len(assigned) == 1:
        return next(iter(assigned))
    if not assigned:
        raise HTTPException(403, "account has no client assigned; contact an administrator")
    raise HTTPException(
        400,
        {"error": "client_selection_required", "message": "multiple clients available; client_code required", "available_clients": sorted(assigned)},
    )


async def _authenticate_api_token(raw_token: str, session: DbSession) -> "CurrentUser":
    """Opaque bearer tokens can't be looked up by value (only their argon2
    hash is stored) — a linear scan-and-verify across active tokens is the
    tradeoff for that, acceptable at this framework's expected token count.
    A token inherits its owning user's role/permissions wholesale; there's
    no separate per-token scope restriction here."""
    candidates = (await session.execute(select(ApiToken).where(ApiToken.revoked.is_(False)))).scalars().all()
    for candidate in candidates:
        if _pwd.verify(raw_token, candidate.token_hash):
            candidate.last_used_at = datetime.now(timezone.utc)
            await session.commit()
            user = (await session.execute(select(User).where(User.id == candidate.user_id))).scalar_one_or_none()
            if user is None or not user.is_active:
                raise HTTPException(401, "account disabled")
            is_admin, module_permissions = merge_roles(user.roles)
            # Bearer tokens carry no client selection of their own — always
            # the token owner's resolved default/only client.
            client_code = _resolve_client_code(user, None)
            return CurrentUser(
                id=str(user.id), username=user.username, display_name=user.display_name,
                is_admin=is_admin, module_permissions=module_permissions, theme=user.theme,
                client_code=client_code,
            )
    raise HTTPException(401, "invalid API token")


async def get_current_user(request: Request, session: DbSession) -> CurrentUser:
    """Every previous route in this API was reachable by anyone who could
    reach the port — login existed, but nothing ever required it. This is
    the dependency that closes that: a valid, non-revoked session cookie is
    now mandatory everywhere it's wired in (see require_permission/
    require_admin below, and their use in data.py/modules.py)."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer ") and auth_header[7:].startswith("mf_"):
        return await _authenticate_api_token(auth_header[7:], session)

    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        raise HTTPException(401, "not authenticated")
    try:
        payload = jwt.decode(token, settings.session_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid session") from None

    # The JWT alone can't be revoked before its exp — the jti->user_id
    # mapping in Valkey is the actual source of truth for "is this session
    # still live"; logout deletes it, so a stolen-but-logged-out cookie
    # fails here even though the token itself still verifies.
    #
    # But Valkey being unreachable is not the same as the session being
    # revoked — cache.py's own contract is that a cache outage degrades
    # performance, not availability. When Valkey can't be reached at all we
    # fall back to trusting the JWT's own signature+expiry (already verified
    # above) instead of hard-locking out every session in the process.
    cached_user_id = await cache.get_session_or_unavailable(payload["jti"])
    if cached_user_id is None:
        raise HTTPException(401, "session expired or revoked")

    # force_logout_epoch already fails soft to None via cache._safe(), so an
    # unreachable Valkey simply skips this check rather than blocking login.
    force_logout_epoch = await cache.force_logout_epoch(payload["sub"])
    if force_logout_epoch is not None and payload["iat"] < force_logout_epoch:
        raise HTTPException(401, "session revoked")

    user = (await session.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(401, "account disabled")

    # Re-validated against the user's *current* assignments on every
    # request, not just trusted from the JWT claim — an admin revoking a
    # user's access to a client must take effect immediately, not only on
    # the next login. A still-valid JWT whose embedded client_code has since
    # been unassigned falls back to whatever the user still resolves to
    # rather than silently keeping the stale one.
    client_code = payload.get("client_code")
    if client_code not in {c.code for c in user.clients}:
        client_code = None
    client_code = _resolve_client_code(user, client_code)

    is_admin, module_permissions = merge_roles(user.roles)
    return CurrentUser(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        is_admin=is_admin,
        module_permissions=module_permissions,
        theme=user.theme,
        client_code=client_code,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


async def get_repository(session: DbSession, registry: Registry, user: CurrentUserDep) -> DataRepository:
    return DataRepository(session, registry, client_code=user.client_code)


Repository = Annotated[DataRepository, Depends(get_repository)]


def require_permission(action: str):
    """Dependency factory: `module` must be a path parameter on the route
    it's used on. Default-deny — a module absent from the role's
    `module_permissions` map, or missing this specific action key, means
    no access, not "assume yes." Admin roles bypass this entirely."""

    async def _check(module: str, user: CurrentUserDep) -> CurrentUser:
        if user.is_admin:
            return user
        allowed = bool(user.module_permissions.get(module, {}).get(action))
        if not allowed:
            raise HTTPException(403, f"not permitted: {action} on {module}")
        return user

    return _check


async def require_admin(user: CurrentUserDep) -> CurrentUser:
    """/admin/builder and /admin/roles change what every user can do and
    see — gated to admin roles only, not just "logged in.\""""
    if not user.is_admin:
        raise HTTPException(403, "admin role required")
    return user


AdminUser = Annotated[CurrentUser, Depends(require_admin)]
