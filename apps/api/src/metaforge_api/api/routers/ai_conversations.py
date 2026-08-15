"""Browse/delete saved AI-chat conversations. Message read/write during an
active chat turn lives in ai_chat.py (it needs to run inside that same
request); this router is purely for the sidebar list + delete + reopening
an old conversation.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func, select

from metaforge_api.api.deps import CurrentUserDep, DbSession
from metaforge_api.infrastructure.models import AiConversation, AiConversationMessage

router = APIRouter(prefix="/api/ai/conversations", tags=["ai-chat"])


class ConversationOut(BaseModel):
    id: str
    seq_number: int
    title: str
    updated_at: str
    message_count: int


@router.get("")
async def list_conversations(session: DbSession, user: CurrentUserDep):
    rows = (
        await session.execute(
            select(AiConversation, func.count(AiConversationMessage.id))
            .outerjoin(AiConversationMessage, AiConversationMessage.conversation_id == AiConversation.id)
            .where(AiConversation.user_id == uuid.UUID(user.id), AiConversation.client_code == user.client_code)
            .group_by(AiConversation.id)
            .order_by(AiConversation.seq_number.desc())
        )
    ).all()
    return [
        {
            "id": str(c.id),
            "seq_number": c.seq_number,
            "title": c.title,
            "updated_at": c.updated_at.isoformat(),
            "message_count": count,
        }
        for c, count in rows
    ]


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    convo = (await session.execute(select(AiConversation).where(AiConversation.id == conversation_id))).scalar_one_or_none()
    if convo is None or str(convo.user_id) != user.id or convo.client_code != user.client_code:
        raise HTTPException(404, "conversation not found")
    messages = (
        await session.execute(
            select(AiConversationMessage)
            .where(AiConversationMessage.conversation_id == conversation_id)
            .order_by(AiConversationMessage.created_at.asc())
        )
    ).scalars().all()
    return {
        "id": str(convo.id),
        "seq_number": convo.seq_number,
        "title": convo.title,
        "messages": [
            {"id": str(m.id), "role": m.role, "content": m.content, "has_image": m.image_data is not None} for m in messages
        ],
    }


@router.get("/{conversation_id}/messages/{message_id}/image")
async def get_message_image(conversation_id: uuid.UUID, message_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    convo = (await session.execute(select(AiConversation).where(AiConversation.id == conversation_id))).scalar_one_or_none()
    if convo is None or str(convo.user_id) != user.id or convo.client_code != user.client_code:
        raise HTTPException(404, "conversation not found")
    message = (
        await session.execute(
            select(AiConversationMessage).where(
                AiConversationMessage.id == message_id, AiConversationMessage.conversation_id == conversation_id
            )
        )
    ).scalar_one_or_none()
    if message is None or message.image_data is None:
        raise HTTPException(404, "image not found")
    return Response(content=message.image_data, media_type=message.image_mime_type or "image/jpeg")


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    convo = (await session.execute(select(AiConversation).where(AiConversation.id == conversation_id))).scalar_one_or_none()
    if convo is None:
        return
    if str(convo.user_id) != user.id or convo.client_code != user.client_code:
        # Same "don't even reveal existence" posture as everywhere else in
        # this app that scopes by tenant+owner — a 404 not a 403.
        raise HTTPException(404, "conversation not found")
    await session.delete(convo)
    await session.commit()
