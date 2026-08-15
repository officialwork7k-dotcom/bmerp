"""Self-service Telegram account linking: short-lived one-time codes
(TelegramLinkCode) that get exchanged for a permanent chat_id<->user
mapping (TelegramLink). Shared by the per-user HTTP router
(api/routers/telegram_link.py, which only ever GENERATES codes) and the
bot's `/link` command handler (infrastructure/telegram_handler.py, which
only ever CONSUMES them) — split out here so neither has to import the
other."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.infrastructure.models import TelegramLink, TelegramLinkCode

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I — unambiguous when read aloud/typed
_CODE_LENGTH = 8
_CODE_TTL = timedelta(minutes=10)


class LinkCodeError(Exception):
    """Raised for any rejection the caller should show as a plain message
    — expired/unknown code, chat already linked to someone else."""


def _generate_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


async def generate_link_code(session: AsyncSession, user_id: str) -> TelegramLinkCode:
    """One live code per user — generating a new one invalidates any
    still-outstanding code for that user."""
    uid = uuid.UUID(user_id)
    await session.execute(delete(TelegramLinkCode).where(TelegramLinkCode.user_id == uid))
    row = TelegramLinkCode(user_id=uid, code=_generate_code(), expires_at=datetime.now(timezone.utc) + _CODE_TTL)
    session.add(row)
    await session.commit()
    return row


async def consume_link_code(
    session: AsyncSession, *, code: str, telegram_chat_id: int, telegram_username: str | None
) -> TelegramLink:
    """Validates + deletes the code (single-use — a deleted row can never
    be replayed), then creates or updates the TelegramLink for that user.
    Raises LinkCodeError with a user-facing message on any rejection."""
    normalized = code.strip().upper()
    row = (await session.execute(select(TelegramLinkCode).where(TelegramLinkCode.code == normalized))).scalar_one_or_none()
    if row is None:
        raise LinkCodeError("That code wasn't found — it may have expired or already been used. Generate a fresh one in MetaForge under AI Assistant settings.")
    if row.expires_at < datetime.now(timezone.utc):
        await session.execute(delete(TelegramLinkCode).where(TelegramLinkCode.id == row.id))
        await session.commit()
        raise LinkCodeError("That code has expired — generate a fresh one in MetaForge under AI Assistant settings.")

    user_id = row.user_id
    await session.execute(delete(TelegramLinkCode).where(TelegramLinkCode.id == row.id))

    existing_for_chat = (
        await session.execute(select(TelegramLink).where(TelegramLink.telegram_chat_id == telegram_chat_id))
    ).scalar_one_or_none()
    if existing_for_chat is not None and existing_for_chat.user_id != user_id:
        await session.commit()  # still consume the code even on rejection — it was used
        raise LinkCodeError("This Telegram account is already linked to a different MetaForge user — unlink it there first.")

    existing_for_user = (await session.execute(select(TelegramLink).where(TelegramLink.user_id == user_id))).scalar_one_or_none()
    if existing_for_user is not None:
        # Relinking from a new chat_id (e.g. a new phone) — replace, and
        # drop the conversation pointer since it belonged to the old chat.
        existing_for_user.telegram_chat_id = telegram_chat_id
        existing_for_user.telegram_username = telegram_username
        existing_for_user.conversation_id = None
        link = existing_for_user
    else:
        link = TelegramLink(user_id=user_id, telegram_chat_id=telegram_chat_id, telegram_username=telegram_username)
        session.add(link)

    await session.commit()
    return link


async def unlink(session: AsyncSession, user_id: str) -> bool:
    result = await session.execute(delete(TelegramLink).where(TelegramLink.user_id == uuid.UUID(user_id)))
    await session.commit()
    return result.rowcount > 0


async def get_link_for_user(session: AsyncSession, user_id: str) -> TelegramLink | None:
    return (await session.execute(select(TelegramLink).where(TelegramLink.user_id == uuid.UUID(user_id)))).scalar_one_or_none()


async def get_link_for_chat(session: AsyncSession, telegram_chat_id: int) -> TelegramLink | None:
    return (await session.execute(select(TelegramLink).where(TelegramLink.telegram_chat_id == telegram_chat_id))).scalar_one_or_none()
