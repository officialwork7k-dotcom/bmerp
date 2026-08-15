"""Admin-only config for the AI chat assistant — deliberately its own
router/table rather than a business module field (see AiSettings'
docstring in infrastructure/models.py for why). Every read masks the two
key fields to a boolean; the raw value is never returned once saved, same
"write-only secret" pattern as webhooks.py's `secret` / tokens.py.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from metaforge_api.api.deps import AdminUser, DbSession
from metaforge_api.infrastructure import llm
from metaforge_api.infrastructure.models import AiSettings
from metaforge_api.infrastructure.telegram_api import TelegramApi, TelegramApiError

router = APIRouter(prefix="/api/admin/ai-settings", tags=["ai-settings"])


class AiSettingsIn(BaseModel):
    enabled: bool = False
    provider: str = "gemini"
    gemini_api_key: str | None = None  # None = leave existing key unchanged; "" = clear it
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    auto_post_amount_cap: float | None = None
    write_allowed_modules: list[dict] = []
    discount_tax_treatment: str = "before_tax"  # before_tax|after_tax — see AiSettings model docstring
    telegram_enabled: bool = False
    telegram_bot_token: str | None = None  # None = leave unchanged; "" = clear it — same contract as the API keys
    public_base_url: str | None = None


async def _get_singleton(session) -> AiSettings | None:
    return (await session.execute(select(AiSettings).order_by(AiSettings.created_at.asc()).limit(1))).scalar_one_or_none()


def _out(row: AiSettings | None) -> dict:
    if row is None:
        return {
            "enabled": False, "provider": "gemini", "gemini_model": "gemini-2.0-flash", "openai_model": "gpt-4o-mini",
            "gemini_key_set": False, "openai_key_set": False, "auto_post_amount_cap": None, "write_allowed_modules": [],
            "discount_tax_treatment": "before_tax",
            "telegram_enabled": False, "telegram_token_set": False, "telegram_bot_username": None, "public_base_url": None,
        }
    return {
        "enabled": row.enabled,
        "provider": row.provider,
        "gemini_model": row.gemini_model,
        "openai_model": row.openai_model,
        "gemini_key_set": bool(row.gemini_api_key),
        "openai_key_set": bool(row.openai_api_key),
        "auto_post_amount_cap": float(row.auto_post_amount_cap) if row.auto_post_amount_cap is not None else None,
        "write_allowed_modules": row.write_allowed_modules,
        "discount_tax_treatment": row.discount_tax_treatment,
        "telegram_enabled": row.telegram_enabled,
        "telegram_token_set": bool(row.telegram_bot_token),
        "telegram_bot_username": row.telegram_bot_username,
        "public_base_url": row.public_base_url,
    }


@router.get("")
async def get_ai_settings(session: DbSession, _: AdminUser):
    return _out(await _get_singleton(session))


@router.put("")
async def save_ai_settings(body: AiSettingsIn, session: DbSession, _: AdminUser):
    row = await _get_singleton(session)
    if row is None:
        row = AiSettings()
        session.add(row)
    row.enabled = body.enabled
    row.provider = body.provider
    row.gemini_model = body.gemini_model
    row.openai_model = body.openai_model
    row.auto_post_amount_cap = body.auto_post_amount_cap
    row.write_allowed_modules = body.write_allowed_modules
    if body.discount_tax_treatment in ("before_tax", "after_tax"):
        row.discount_tax_treatment = body.discount_tax_treatment
    row.telegram_enabled = body.telegram_enabled
    row.public_base_url = (body.public_base_url or "").rstrip("/") or None
    # Only overwrite a key when the caller actually sent a non-empty
    # value — the frontend never has the real key to re-send (masked on
    # read), so omitting/blanking the field must mean "leave it alone,"
    # not "wipe it." An explicit empty string is the only way to clear one.
    if body.gemini_api_key is not None:
        row.gemini_api_key = body.gemini_api_key or None
    if body.openai_api_key is not None:
        row.openai_api_key = body.openai_api_key or None
    if body.telegram_bot_token is not None:
        row.telegram_bot_token = body.telegram_bot_token or None
        if not body.telegram_bot_token:
            row.telegram_bot_username = None  # cleared token means the stored username is stale too
    await session.commit()
    return _out(row)


class VerifyTelegramIn(BaseModel):
    # Same "not-yet-saved key" convenience as ListModelsIn.
    token: str | None = None


@router.post("/telegram/verify")
async def verify_telegram_token(body: VerifyTelegramIn, session: DbSession, _: AdminUser):
    row = await _get_singleton(session)
    token = body.token or (row.telegram_bot_token if row else None)
    if not token:
        raise HTTPException(400, "No bot token saved — enter one first")
    api = TelegramApi(token)
    try:
        me = await api.get_me()
    except TelegramApiError as exc:
        raise HTTPException(400, f"Could not verify bot token: {exc}") from exc
    finally:
        await api.aclose()
    username = me.get("username")
    if row is not None:
        row.telegram_bot_username = username
        await session.commit()
    return {"ok": True, "bot_username": username}


class ListModelsIn(BaseModel):
    provider: str
    # A key the admin just typed but hasn't saved yet — lets "list models"
    # work before the first Save, without ever persisting it if they end
    # up cancelling. Omit to use the already-saved key for that provider.
    api_key: str | None = None


@router.post("/models")
async def list_ai_models(body: ListModelsIn, session: DbSession, _: AdminUser):
    api_key = body.api_key
    if not api_key:
        row = await _get_singleton(session)
        api_key = (row.gemini_api_key if body.provider == "gemini" else row.openai_api_key) if row else None
        if not api_key:
            raise HTTPException(400, f"No API key saved for provider '{body.provider}' — enter one first")
    try:
        models = await llm.list_models(provider=body.provider, api_key=api_key)
    except llm.LlmError as exc:
        raise HTTPException(400, f"Could not list models: {exc}") from exc
    return {"models": models}
