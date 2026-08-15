"""The AI chat HTTP endpoint — thin wrapper over infrastructure/
chat_service.py's run_chat_turn(), which holds all the actual logic
(shared with the Telegram integration; see that module's docstring for
why it's split out this way)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from metaforge_api.api.deps import CurrentUserDep, DbSession, Registry, Repository
from metaforge_api.infrastructure import chat_service

router = APIRouter(prefix="/api/ai", tags=["ai-chat"])


class ChatImageIn(BaseModel):
    mime_type: str
    data: str  # base64, no "data:" prefix


class ChatIn(BaseModel):
    message: str = ""
    conversation_id: str | None = None
    image: ChatImageIn | None = None


@router.post("/chat")
async def chat(body: ChatIn, session: DbSession, registry: Registry, user: CurrentUserDep, repo: Repository):
    return await chat_service.run_chat_turn(
        session=session,
        registry=registry,
        user=user,
        repo=repo,
        message=body.message,
        image=body.image.model_dump() if body.image else None,
        conversation_id=body.conversation_id,
    )
