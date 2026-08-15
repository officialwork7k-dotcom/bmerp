"""ARQ worker process entry point: `arq metaforge_api.worker.WorkerSettings`.

Runs as the one separate process in the deployment topology (VM budget:
300MB ceiling, max_jobs=5 concurrent slots — see the plan's RAM table).
Outbound webhook delivery lives here. (CSV import/export used to as well —
moved to synchronous request handling in csv_io.py; see that module's
docstring for why relying on this worker + Valkey for it was a real hang
risk, not just an ops inconvenience, whenever either was unreachable.)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any

import httpx
from sqlalchemy import select

from metaforge_api.infrastructure.db import async_session_factory
from metaforge_api.infrastructure.jobs import redis_settings
from metaforge_api.infrastructure.models import Webhook


async def deliver_webhook(ctx: dict[str, Any], webhook_id: str, event: str, module: str, record_id: str, payload: dict[str, Any]) -> None:
    """HMAC-SHA256 signed delivery (`X-MetaForge-Signature` header, same
    pattern as GitHub/Stripe) so a receiver can verify the payload actually
    came from this server, not just that it hit the right URL."""
    async with async_session_factory() as session:
        hook = (await session.execute(select(Webhook).where(Webhook.id == uuid.UUID(webhook_id)))).scalar_one_or_none()
        if hook is None or not hook.is_active:
            return
        body = json.dumps({"event": event, "module": module, "record_id": record_id, "data": payload}).encode()
        signature = hmac.new(hook.secret.encode(), body, hashlib.sha256).hexdigest()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(hook.url, content=body, headers={"Content-Type": "application/json", "X-MetaForge-Signature": signature})
        except httpx.HTTPError:
            pass  # best-effort delivery; no retry queue at this scale


class WorkerSettings:
    functions = [deliver_webhook]
    redis_settings = redis_settings()
    max_jobs = 5
