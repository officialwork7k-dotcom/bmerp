"""Turns one Telegram update into a chat_service.run_chat_turn() call (or
a command reply) — the only Telegram-specific code in the whole feature;
everything downstream of build_telegram_actor()/run_chat_turn() is the
exact same code path a web chat message takes, guardrails included.

Security note worth stating explicitly: private chats only (see
handle_update) — an ERP assistant answering in a Telegram group would
leak business data to every member of that group. Every other identity/
permission/tenant check is inherited for free from run_chat_turn and the
CurrentUser it's handed (see build_telegram_actor), re-resolved fresh on
every single message — a deactivated user or a pulled role/client
assignment takes effect on their very next Telegram message, same
freshness as the web session dependency it mirrors.
"""

from __future__ import annotations

import html
import logging
import re
import traceback
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.api.deps import CurrentUser, _resolve_client_code, merge_roles
from metaforge_api.infrastructure import chat_service, telegram_link_service
from metaforge_api.infrastructure.image_prep import ImagePrepError, preprocess_receipt_image
from metaforge_api.infrastructure.models import TelegramLink, User
from metaforge_api.infrastructure.module_registry import SessionModuleRegistry
from metaforge_api.infrastructure.repository import DataRepository
from metaforge_api.infrastructure.telegram_api import TelegramApi

logger = logging.getLogger("metaforge.telegram")

_ALLOWED_IMAGE_DOCUMENT_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_TELEGRAM_FILE_BYTES = 20 * 1024 * 1024  # Telegram bots can't download bigger files than this anyway


async def build_telegram_actor(session: AsyncSession, link: TelegramLink) -> tuple[CurrentUser, SessionModuleRegistry, DataRepository]:
    """Mirrors api/deps.py's get_current_user/get_repository tail for an
    identity that didn't arrive via an HTTP session cookie. Re-loads the
    User and re-merges roles every call — no caching — so account
    deactivation or a role/client change is picked up on the very next
    Telegram message, same as a fresh web request would."""
    user = (await session.execute(select(User).where(User.id == link.user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(401, "your MetaForge account is disabled or no longer exists")

    assigned = {c.code for c in user.clients}
    requested = link.preferred_client_code if link.preferred_client_code in assigned else None
    client_code = _resolve_client_code(user, requested)  # raises HTTPException(400, client_selection_required) if ambiguous

    is_admin, module_permissions = merge_roles(user.roles)
    current_user = CurrentUser(
        id=str(user.id), username=user.username, display_name=user.display_name,
        is_admin=is_admin, module_permissions=module_permissions, theme=user.theme,
        client_code=client_code,
    )
    registry = SessionModuleRegistry()
    await registry.load_all(session)
    repo = DataRepository(session, registry, client_code=client_code)
    return current_user, registry, repo


# ---------------------------------------------------------------------------
# Reply formatting — Telegram's HTML parse_mode, not MarkdownV2 (which
# requires escaping ~18 characters in free-form assistant prose; one missed
# character 400s the whole message). Only what the assistant's replies
# actually contain needs handling: **bold**, *italic*/_italic_, `code`,
# fenced blocks, [label](/module/id) internal links, headings, "- " lists.
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```(?:\w+)?\n?(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^#{1,6}[ \t]+(.*)$", re.MULTILINE)
_BULLET_RE = re.compile(r"^[ \t]*[-*][ \t]+", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)([^*\n]+)\*(?!\*)|(?<!\w)_([^_\n]+)_(?!\w)")


def markdown_to_telegram_html(text: str, *, base_url: str | None) -> str:
    if not text:
        return text

    code_blocks: list[str] = []
    text = _CODE_FENCE_RE.sub(lambda m: _stash(code_blocks, html.escape(m.group(1), quote=False), "CODEBLOCK"), text)

    inline_codes: list[str] = []
    text = _INLINE_CODE_RE.sub(lambda m: _stash(inline_codes, html.escape(m.group(1), quote=False), "INLINECODE"), text)

    links: list[tuple[str, str | None]] = []

    def _stash_link(m: re.Match) -> str:
        label, target = html.escape(m.group(1), quote=False), m.group(2)
        href = f"{base_url}{target}" if base_url and target.startswith("/") else None
        links.append((label, href))
        return f"\x00LINK{len(links) - 1}\x00"

    text = _LINK_RE.sub(_stash_link, text)
    text = html.escape(text, quote=False)
    text = _HEADING_RE.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = _BULLET_RE.sub("• ", text)
    text = _BOLD_RE.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = _ITALIC_RE.sub(lambda m: f"<i>{m.group(1) or m.group(2)}</i>", text)

    for i, (label, href) in enumerate(links):
        replacement = f'<a href="{html.escape(href, quote=True)}">{label}</a>' if href else label
        text = text.replace(f"\x00LINK{i}\x00", replacement)
    for i, code in enumerate(inline_codes):
        text = text.replace(f"\x00INLINECODE{i}\x00", f"<code>{code}</code>")
    for i, code in enumerate(code_blocks):
        text = text.replace(f"\x00CODEBLOCK{i}\x00", f"<pre>{code}</pre>")
    return text


def _stash(store: list[str], value: str, tag: str) -> str:
    store.append(value)
    return f"\x00{tag}{len(store) - 1}\x00"


def split_for_telegram(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        parts.append(remaining)
    return parts


async def _reply(api: TelegramApi, chat_id: int, text: str, *, base_url: str | None) -> None:
    html_text = markdown_to_telegram_html(text, base_url=base_url)
    for chunk in split_for_telegram(html_text):
        try:
            await api.send_message(chat_id=chat_id, text=chunk, parse_mode="HTML")
        except Exception:
            # Malformed-entity 400s and similar — a plain-text reply always
            # beats a silently dropped one.
            await api.send_message(chat_id=chat_id, text=re.sub(r"<[^>]+>", "", chunk), parse_mode=None)


# ---------------------------------------------------------------------------
# Update handling
# ---------------------------------------------------------------------------


async def handle_update(update: dict[str, Any], *, session_factory, api: TelegramApi, base_url: str | None) -> None:
    message = update.get("message")
    if not message:
        return  # not a message update (edited_message, channel_post, ...) — ignored in v1
    chat = message.get("chat") or {}
    if chat.get("type") != "private":
        return  # groups/channels never reach the assistant — see module docstring

    chat_id = chat["id"]
    text = (message.get("text") or "").strip()
    caption = (message.get("caption") or "").strip()

    async with session_factory() as session:
        try:
            await _handle_message(session, message, chat_id=chat_id, text=text, caption=caption, api=api, base_url=base_url)
        except HTTPException as exc:
            await _reply(api, chat_id, str(exc.detail), base_url=base_url)
        except Exception:
            logger.exception("unhandled error processing Telegram update %s", update.get("update_id"))
            await _reply(api, chat_id, "Something went wrong handling that — please try again.", base_url=base_url)


async def _handle_message(session: AsyncSession, message: dict[str, Any], *, chat_id: int, text: str, caption: str, api: TelegramApi, base_url: str | None) -> None:
    from_user = message.get("from") or {}
    telegram_username = from_user.get("username")

    if text.startswith("/"):
        handled = await _dispatch_command(session, text, chat_id=chat_id, telegram_username=telegram_username, api=api, base_url=base_url)
        if handled:
            return

    link = await telegram_link_service.get_link_for_chat(session, chat_id)
    if link is None:
        await _reply(
            api, chat_id,
            "This Telegram account isn't linked to a MetaForge user yet. Generate a link code from AI Assistant "
            "settings in MetaForge, then send it here as /link CODE.",
            base_url=base_url,
        )
        return

    photo_file_id = _extract_image_file_id(message)
    if photo_file_id is None and message.get("document") is not None:
        await _reply(api, chat_id, "I can read photos of receipts/invoices — send the image as a photo or an image file.", base_url=base_url)
        return

    image_payload: dict[str, str] | None = None
    if photo_file_id is not None:
        try:
            image_payload = await _download_and_preprocess(api, photo_file_id)
        except ImagePrepError as exc:
            await _reply(api, chat_id, str(exc), base_url=base_url)
            return

    turn_message = caption if photo_file_id is not None else text
    await api.send_chat_action(chat_id=chat_id, action="upload_photo" if image_payload else "typing")

    try:
        current_user, registry, repo = await build_telegram_actor(session, link)
    except HTTPException as exc:
        if isinstance(exc.detail, dict) and exc.detail.get("error") == "client_selection_required":
            codes = ", ".join(exc.detail.get("available_clients", []))
            await _reply(api, chat_id, f"You have access to multiple organizations ({codes}) — pick one with /org CODE first.", base_url=base_url)
            return
        raise

    conversation_id = str(link.conversation_id) if link.conversation_id else None
    try:
        result = await chat_service.run_chat_turn(
            session=session, registry=registry, user=current_user, repo=repo,
            message=turn_message, image=image_payload, conversation_id=conversation_id,
        )
    except HTTPException as exc:
        if exc.status_code == 404 and conversation_id:
            # The conversation this link pointed at is gone (deleted, or a
            # stale pointer from before an /org switch) — drop the pointer
            # and retry once as a fresh conversation rather than wedging
            # this link forever.
            link.conversation_id = None
            await session.commit()
            result = await chat_service.run_chat_turn(
                session=session, registry=registry, user=current_user, repo=repo,
                message=turn_message, image=image_payload, conversation_id=None,
            )
        else:
            raise

    new_conversation_id = uuid.UUID(result["conversation_id"])
    if link.conversation_id != new_conversation_id:
        link.conversation_id = new_conversation_id
        await session.commit()

    await _reply(api, chat_id, result["reply"], base_url=base_url)


def _extract_image_file_id(message: dict[str, Any]) -> str | None:
    """Telegram photos arrive as an array of PhotoSize ordered
    smallest->largest; the last is the highest resolution. A document is
    only treated as an image if its declared mime type says so (users
    sometimes send receipts as files to dodge Telegram's photo
    recompression)."""
    photos = message.get("photo")
    if photos:
        return photos[-1]["file_id"]
    document = message.get("document")
    if document and document.get("mime_type") in _ALLOWED_IMAGE_DOCUMENT_MIME_TYPES:
        return document["file_id"]
    return None


async def _download_and_preprocess(api: TelegramApi, file_id: str) -> dict[str, str]:
    import base64

    file_path = await api.get_file(file_id=file_id)
    raw = await api.download_file(file_path=file_path)
    if len(raw) > _MAX_TELEGRAM_FILE_BYTES:
        raise ImagePrepError("That photo is too large — try a lower-resolution shot.")
    prepped = preprocess_receipt_image(raw)
    return {"mime_type": prepped.mime_type, "data": base64.b64encode(prepped.data).decode()}


# ---------------------------------------------------------------------------
# Commands — never reach the AI; handled entirely here.
# ---------------------------------------------------------------------------


async def _dispatch_command(
    session: AsyncSession, text: str, *, chat_id: int, telegram_username: str | None, api: TelegramApi, base_url: str | None
) -> bool:
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0]  # strip a possible @botname suffix
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/start", "/link"):
        if not arg:
            await _reply(
                api, chat_id,
                "Send /link CODE with the code from MetaForge's AI Assistant settings to connect your account.",
                base_url=base_url,
            )
            return True
        try:
            await telegram_link_service.consume_link_code(session, code=arg, telegram_chat_id=chat_id, telegram_username=telegram_username)
        except telegram_link_service.LinkCodeError as exc:
            await _reply(api, chat_id, str(exc), base_url=base_url)
            return True
        await _reply(api, chat_id, "Linked! You can now chat here just like the MetaForge AI Assistant panel — including sending receipt/invoice photos.", base_url=base_url)
        return True

    if cmd == "/unlink":
        link = await telegram_link_service.get_link_for_chat(session, chat_id)
        if link is None:
            await _reply(api, chat_id, "This Telegram account isn't linked to anything.", base_url=base_url)
            return True
        await telegram_link_service.unlink(session, str(link.user_id))
        await _reply(api, chat_id, "Unlinked.", base_url=base_url)
        return True

    if cmd == "/new":
        link = await telegram_link_service.get_link_for_chat(session, chat_id)
        if link is not None:
            link.conversation_id = None
            await session.commit()
        await _reply(api, chat_id, "Started a fresh conversation.", base_url=base_url)
        return True

    if cmd == "/org":
        link = await telegram_link_service.get_link_for_chat(session, chat_id)
        if link is None:
            await _reply(api, chat_id, "Link your account first with /link CODE.", base_url=base_url)
            return True
        user = (await session.execute(select(User).where(User.id == link.user_id))).scalar_one_or_none()
        if user is None:
            await _reply(api, chat_id, "Your MetaForge account could not be found.", base_url=base_url)
            return True
        codes = sorted(c.code for c in user.clients)
        if not arg:
            active = link.preferred_client_code or "(default)"
            await _reply(api, chat_id, f"Your organizations: {', '.join(codes) or 'none'}. Active: {active}. Use /org CODE to switch.", base_url=base_url)
            return True
        target = arg.strip().upper()
        if target not in codes:
            await _reply(api, chat_id, f"You don't have access to '{target}'. Your organizations: {', '.join(codes)}.", base_url=base_url)
            return True
        link.preferred_client_code = target
        link.conversation_id = None  # conversations are client-scoped — start fresh under the new org
        await session.commit()
        await _reply(api, chat_id, f"Switched to {target}.", base_url=base_url)
        return True

    if cmd == "/help":
        await _reply(
            api, chat_id,
            "Commands:\n/link CODE — connect your MetaForge account\n/unlink — disconnect\n"
            "/org [CODE] — show or switch organization\n/new — start a fresh conversation\n"
            "Anything else is sent straight to the AI assistant — text or a receipt/invoice photo.",
            base_url=base_url,
        )
        return True

    return False
