"""Thin, injectable Telegram Bot API REST client — plain httpx, no SDK,
same philosophy as infrastructure/llm.py. Every error message is scrubbed
of the bot token before it can end up in a log line or a reply to a user.

Deliberately a class (not module-level functions) so callers — the
long-poller (telegram_poller.py) and its update handler
(telegram_handler.py) — take an `api: TelegramApi` parameter rather than
making raw httpx calls inline. That's what makes both testable without a
live bot: tests construct a fake with the same method signatures.
"""

from __future__ import annotations

from typing import Any

import httpx

_API_ROOT = "https://api.telegram.org"
_TIMEOUT = 35.0  # a getUpdates long-poll asks for up to 30s server-side; leave headroom


class TelegramApiError(Exception):
    pass


class TelegramConflictError(TelegramApiError):
    """409 from getUpdates — another process is polling this same bot
    token concurrently (e.g. two API workers). See telegram_poller.py."""


def _scrub(text: str, token: str) -> str:
    return text.replace(token, "bot***") if token else text


class TelegramApi:
    def __init__(self, token: str, *, client: httpx.AsyncClient | None = None):
        self._token = token
        self._client = client or httpx.AsyncClient(timeout=_TIMEOUT)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _url(self, method: str) -> str:
        return f"{_API_ROOT}/bot{self._token}/{method}"

    async def _call(self, method: str, **params: Any) -> Any:
        try:
            resp = await self._client.post(self._url(method), json={k: v for k, v in params.items() if v is not None})
        except httpx.HTTPError as exc:
            raise TelegramApiError(_scrub(f"network error calling {method}: {exc}", self._token)) from exc
        if resp.status_code == 409:
            raise TelegramConflictError(_scrub(f"{method}: 409 conflict — another poller is using this bot token", self._token))
        if resp.status_code >= 400:
            raise TelegramApiError(_scrub(f"{method}: {resp.status_code} {resp.text[:500]}", self._token))
        data = resp.json()
        if not data.get("ok"):
            raise TelegramApiError(_scrub(f"{method}: {data.get('description', 'unknown error')}", self._token))
        return data["result"]

    async def get_updates(self, *, offset: int | None, timeout: int = 25) -> list[dict[str, Any]]:
        return await self._call("getUpdates", offset=offset, timeout=timeout, allowed_updates=["message"])

    async def send_message(self, *, chat_id: int, text: str, parse_mode: str | None = "HTML") -> None:
        await self._call("sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode, disable_web_page_preview=True)

    async def send_chat_action(self, *, chat_id: int, action: str = "typing") -> None:
        await self._call("sendChatAction", chat_id=chat_id, action=action)

    async def get_file(self, *, file_id: str) -> str:
        result = await self._call("getFile", file_id=file_id)
        return result["file_path"]

    async def download_file(self, *, file_path: str) -> bytes:
        url = f"{_API_ROOT}/file/bot{self._token}/{file_path}"
        try:
            resp = await self._client.get(url)
        except httpx.HTTPError as exc:
            raise TelegramApiError(_scrub(f"network error downloading file: {exc}", self._token)) from exc
        if resp.status_code >= 400:
            raise TelegramApiError(_scrub(f"file download: {resp.status_code}", self._token))
        return resp.content

    async def get_me(self) -> dict[str, Any]:
        return await self._call("getMe")
