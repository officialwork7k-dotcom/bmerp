"""Per-user Telegram account linking — generate a one-time code here,
then send it to the bot (`/link CODE`) to connect. See infrastructure/
telegram_link_service.py for the actual generate/consume logic; this
router only ever generates (consumption happens from the bot side, in
infrastructure/telegram_handler.py)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from metaforge_api.api.deps import CurrentUserDep, DbSession
from metaforge_api.infrastructure import chat_service, telegram_link_service

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/link-code")
async def create_link_code(session: DbSession, user: CurrentUserDep):
    ai_settings = await chat_service.load_ai_settings(session)
    if ai_settings is None or not ai_settings.telegram_enabled:
        raise HTTPException(400, "Telegram integration is not enabled on this instance")
    row = await telegram_link_service.generate_link_code(session, user.id)
    bot_username = ai_settings.telegram_bot_username
    return {
        "code": row.code,
        "expires_at": row.expires_at.isoformat(),
        "bot_username": bot_username,
        "deep_link": f"https://t.me/{bot_username}?start={row.code}" if bot_username else None,
    }


@router.get("/link")
async def get_link(session: DbSession, user: CurrentUserDep):
    link = await telegram_link_service.get_link_for_user(session, user.id)
    if link is None:
        return {"linked": False}
    return {
        "linked": True,
        "telegram_username": link.telegram_username,
        "linked_at": link.linked_at.isoformat(),
        "preferred_client_code": link.preferred_client_code,
    }


@router.delete("/link")
async def delete_link(session: DbSession, user: CurrentUserDep):
    await telegram_link_service.unlink(session, user.id)
    return {"ok": True}
