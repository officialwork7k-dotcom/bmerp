"""Thin Valkey wrapper — used purely as a cache (module metadata, sessions),
per the required stack: "treat it purely as a cache, never as a system of
record." All keys are safely re-derivable from Postgres, so a flush is
harmless (maxmemory-policy allkeys-lru on the Valkey side).

Every call fails soft: a cache being unreachable must never break a request
(module reads fall back to Postgres, sessions fall back to stateless JWT
verification) — Valkey being down should degrade performance, not
availability.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Awaitable, Callable, TypeVar

from redis.asyncio import Redis
from redis.exceptions import RedisError

from metaforge_api.infrastructure.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

_redis: Redis | None = None
_MODULE_TTL_SECONDS = 300
_SESSION_TTL_SECONDS = 8 * 3600

# Circuit breaker: a get_current_user request makes 2-3 Valkey round trips
# (session check, force-logout check, sometimes a module-cache read). With
# Valkey simply not running in this environment, every one of those calls
# used to pay its own ~0.5s connect-timeout penalty — 1-1.5s of pure
# connection-timeout tax on every single request, the actual cause of the
# "first click slow, repeat clicks still slow" report. Once a failure is
# seen, every call short-circuits to the default immediately (no network
# attempt at all) until this cooldown elapses, then the next call alone
# pays to re-probe. Recovery is automatic: a successful call clears it.
_FAILURE_COOLDOWN_SECONDS = 5.0
_circuit_open_until = 0.0


class Unavailable:
    """Sentinel distinguishing 'Valkey unreachable' from a genuine cache
    miss (a real `None`/missing key). Session-validity checks need this
    distinction — "Valkey is down" must fall back to trusting the JWT's own
    signature+expiry (per this module's own fail-soft policy below), while
    "this session key doesn't exist" must mean the session really is
    revoked/expired. Collapsing both to `None`, as an earlier version of
    _safe() did, made an unreachable cache indistinguishable from every
    session being revoked — i.e. Valkey being down locked every user out
    entirely, exactly the availability-over-performance regression this
    module's own docstring says must never happen."""


UNAVAILABLE = Unavailable()


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        # A short connect timeout bounds the worst case for the one call
        # per cooldown window that actually attempts a connection; the
        # circuit breaker above is what keeps every *other* call near-zero
        # cost while Valkey stays down.
        _redis = Redis.from_url(settings.valkey_url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
    return _redis


async def _safe(fn: Callable[[], Awaitable[T]], default: T | None = None) -> T | None:
    global _circuit_open_until
    now = time.monotonic()
    if now < _circuit_open_until:
        return default
    try:
        result = await fn()
        _circuit_open_until = 0.0
        return result
    except (RedisError, OSError) as exc:
        logger.debug("Valkey unavailable, continuing without cache: %s", exc)
        _circuit_open_until = now + _FAILURE_COOLDOWN_SECONDS
        return default


async def _safe_or_unavailable(fn: Callable[[], Awaitable[T]]) -> T | Unavailable:
    global _circuit_open_until
    now = time.monotonic()
    if now < _circuit_open_until:
        return UNAVAILABLE
    try:
        result = await fn()
        _circuit_open_until = 0.0
        return result
    except (RedisError, OSError) as exc:
        logger.debug("Valkey unavailable: %s", exc)
        _circuit_open_until = now + _FAILURE_COOLDOWN_SECONDS
        return UNAVAILABLE


async def get_cached_module(name: str) -> dict[str, Any] | None:
    raw = await _safe(lambda: get_redis().get(f"module:{name}"))
    return json.loads(raw) if raw else None


async def set_cached_module(name: str, data: dict[str, Any]) -> None:
    await _safe(lambda: get_redis().set(f"module:{name}", json.dumps(data), ex=_MODULE_TTL_SECONDS))


async def invalidate_cached_module(name: str) -> None:
    await _safe(lambda: get_redis().delete(f"module:{name}"))


async def get_cached_ai_directory(fingerprint: str) -> str | None:
    """The AI chat system prompt's per-module directory (infrastructure.
    ai_tools.build_module_directory) is a full scan of every module's
    fields + embedded children — real, avoidable work when it's rebuilt
    from scratch on every single chat request, and worse, resent as part
    of the system prompt on every hop of a multi-tool-call turn. Cached
    under a fingerprint of every module's (name, version) pair, so it
    self-invalidates the moment any module is saved — no explicit
    invalidation call needed anywhere in modules.py."""
    return await _safe(lambda: get_redis().get(f"ai:directory:{fingerprint}"))


async def set_cached_ai_directory(fingerprint: str, directory: str) -> None:
    await _safe(lambda: get_redis().set(f"ai:directory:{fingerprint}", directory, ex=_MODULE_TTL_SECONDS))


async def set_session(token_id: str, user_id: str) -> None:
    await _safe(lambda: get_redis().set(f"session:{token_id}", user_id, ex=_SESSION_TTL_SECONDS))


async def get_session(token_id: str) -> str | None:
    return await _safe(lambda: get_redis().get(f"session:{token_id}"))


async def get_session_or_unavailable(token_id: str) -> str | None | Unavailable:
    """Same lookup as get_session, but lets the caller tell 'Valkey is down'
    apart from 'this session key genuinely isn't set.' Used only by the
    login-session validity check in deps.get_current_user, which needs to
    degrade to stateless JWT trust on the former and hard-reject on the
    latter — see Unavailable's docstring."""
    return await _safe_or_unavailable(lambda: get_redis().get(f"session:{token_id}"))


async def revoke_session(token_id: str) -> None:
    await _safe(lambda: get_redis().delete(f"session:{token_id}"))


async def revoke_all_sessions_for_user(user_id: str) -> None:
    """Individual sessions are only ever indexed jti->user_id, not the
    reverse — enumerating and deleting every live jti for a user would mean
    scanning all of Valkey. Instead, force-logout stamps "any token issued
    before now is void" and get_current_user checks the JWT's `iat` against
    it — same practical effect, no scan required."""
    await _safe(lambda: get_redis().set(f"force_logout:{user_id}", str(int(time.time())), ex=_SESSION_TTL_SECONDS))


async def force_logout_epoch(user_id: str) -> int | None:
    raw = await _safe(lambda: get_redis().get(f"force_logout:{user_id}"))
    return int(raw) if raw else None


async def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    """Fixed-window counter: INCR then set an expiry only on the first hit
    in the window. Returns True if the call is allowed (under `limit`),
    False if it should be rejected. Fails OPEN (allowed) if Valkey is
    unreachable — same fail-soft policy as the rest of this module; a rate
    limit is a courtesy against runaway usage, not a security boundary, so
    degrading to "no limit" beats degrading to "nobody can use the AI
    assistant" when the cache is down."""

    async def _incr() -> int:
        redis = get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        return count

    count = await _safe(_incr, default=0)
    return (count or 0) <= limit
