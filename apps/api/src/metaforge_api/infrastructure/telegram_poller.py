"""Long-polling supervisor for the Telegram integration — lifespan-managed
asyncio task inside the API process (see api/main.py), not ARQ: ARQ has a
documented hang history in this environment (infrastructure/
periodic_runs.py) and its Valkey backend isn't running locally, so a job
on it would simply never start. A separate `python -m` process would work
but adds a second thing to launch for zero benefit at this app's scale —
the API process is already always-on.

Cursor persistence: AiSettings.telegram_update_offset (a DB column, not
Valkey — Valkey isn't running locally, so a Valkey cursor would silently
never persist and every restart would replay the whole backlog).
Semantics are at-least-once: a crash between handling a batch and
committing the new offset replays that batch on restart. This is
accepted, not a bug to fix here — every write in that replay still passes
through the exact same provenance/allowlist/amount-cap guardrails as any
other turn, so the worst case is an annoying duplicate reply, not a
corrupt one. A production deployment big enough to care would swap this
for a webhook + dedup table; nothing here blocks that migration (see
run_poller_forever's docstring for the exact swap point).

Runtime enable/disable: re-reads the settings row every cycle, so an
admin toggling Telegram off takes effect within one cycle (≤ ~15s idle
sleep, or ≤ 25s if a long-poll was already in flight when it happened) —
no process restart required.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from metaforge_api.infrastructure.db import async_session_factory
from metaforge_api.infrastructure.models import AiSettings
from metaforge_api.infrastructure.telegram_api import TelegramApi, TelegramConflictError
from metaforge_api.infrastructure.telegram_handler import handle_update

logger = logging.getLogger("metaforge.telegram")

_DISABLED_POLL_INTERVAL = 15.0
_LONG_POLL_TIMEOUT = 25
_MAX_BACKOFF = 60.0


async def _load_settings() -> AiSettings | None:
    async with async_session_factory() as session:
        return (await session.execute(select(AiSettings).order_by(AiSettings.created_at.asc()).limit(1))).scalar_one_or_none()


async def _advance_offset(new_offset: int) -> None:
    async with async_session_factory() as session:
        row = (await session.execute(select(AiSettings).order_by(AiSettings.created_at.asc()).limit(1))).scalar_one_or_none()
        if row is not None:
            row.telegram_update_offset = new_offset
            await session.commit()


async def run_poller_forever(*, stop_event: asyncio.Event) -> None:
    """The only Telegram-transport-specific parts of this whole feature
    are this function and TelegramApi.get_updates — everything from
    telegram_handler.handle_update down is transport-agnostic by
    construction, which is exactly what a later webhook migration would
    reuse unchanged."""
    api: TelegramApi | None = None
    active_token: str | None = None
    backoff = 1.0

    try:
        while not stop_event.is_set():
            settings_row = await _load_settings()
            token = settings_row.telegram_bot_token if settings_row else None
            enabled = bool(settings_row and settings_row.enabled and settings_row.telegram_enabled and token)

            if not enabled:
                if api is not None:
                    await api.aclose()
                    api = None
                    active_token = None
                await _wait_or_stop(stop_event, _DISABLED_POLL_INTERVAL)
                continue

            if api is None or token != active_token:
                if api is not None:
                    await api.aclose()
                api = TelegramApi(token)
                active_token = token
                logger.info("telegram poller: starting")

            try:
                updates = await api.get_updates(offset=settings_row.telegram_update_offset, timeout=_LONG_POLL_TIMEOUT)
                backoff = 1.0
            except TelegramConflictError as exc:
                logger.warning("telegram poller: %s", exc)
                await _wait_or_stop(stop_event, 60.0)
                continue
            except Exception as exc:
                logger.warning("telegram poller: error fetching updates: %s", exc)
                await _wait_or_stop(stop_event, backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)
                continue

            last_id: int | None = None
            for update in updates:
                try:
                    await handle_update(update, session_factory=async_session_factory, api=api, base_url=settings_row.public_base_url)
                except Exception:
                    # One poison update must never stall the cursor or
                    # kill the loop — log and move on.
                    logger.exception("telegram poller: failed to handle update %s", update.get("update_id"))
                last_id = update["update_id"]

            if last_id is not None:
                await _advance_offset(last_id + 1)
    except asyncio.CancelledError:
        raise
    finally:
        if api is not None:
            await api.aclose()


async def _wait_or_stop(stop_event: asyncio.Event, timeout: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=timeout)
    except TimeoutError:
        pass
