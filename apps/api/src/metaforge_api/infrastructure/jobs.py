"""Thin wrapper around ARQ's public API (enqueue, cron, retry, job status),
per the required stack's caution: ARQ is maintenance-only upstream, so all
call sites should go through this one module — a forced future migration
touches only this file.
"""

from __future__ import annotations

import asyncio
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.jobs import Job, JobStatus

from metaforge_api.infrastructure.settings import settings

_pool: ArqRedis | None = None

# create_pool() retries connecting to Valkey with backoff by default — if
# Valkey is simply down, that's not a quick failure, it's an indefinite
# hang. Every current caller (webhook dispatch in repository.py) already
# wraps enqueue() in try/except expecting a bounded failure, so a hang here
# silently defeats that fail-soft handling and blocks the request that
# triggered it. Bounding the wait turns "hangs forever" into "raises
# TimeoutError promptly", which the caller's except already handles.
_CONNECT_TIMEOUT_SECONDS = 2.0


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.valkey_url)


async def get_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await asyncio.wait_for(create_pool(redis_settings()), timeout=_CONNECT_TIMEOUT_SECONDS)
    return _pool


async def enqueue(function_name: str, *args: Any, **kwargs: Any) -> str:
    pool = await get_pool()
    job = await asyncio.wait_for(pool.enqueue_job(function_name, *args, **kwargs), timeout=_CONNECT_TIMEOUT_SECONDS)
    assert job is not None
    return job.job_id


async def job_status(job_id: str) -> JobStatus:
    pool = await get_pool()
    return await Job(job_id, pool).status()


async def job_result(job_id: str) -> Any:
    """None while still running; the function's return value once complete.
    Only call after job_status() reports complete — .result() blocks/raises
    otherwise."""
    pool = await get_pool()
    job = Job(job_id, pool)
    info = await job.result_info()
    return info.result if info is not None else None
