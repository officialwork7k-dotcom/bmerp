"""DB-backed ModuleRegistry: loads ModuleMetadata from the `modules` table.

A process-local cache keyed on (name, version) avoids re-querying on every
request; a builder save bumps `version`, which naturally invalidates it.
Phase 5 swaps this cache for Valkey without changing the interface.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.domain.metadata import ModuleMetadata
from metaforge_api.domain.serialization import module_from_dict
from metaforge_api.infrastructure.models import Module

_cache: dict[str, ModuleMetadata] = {}


class SessionModuleRegistry:
    """Synchronous-looking `.get()` backed by a cache populated via `.load()`.

    Repository code (see repository.py) expects a synchronous `get()` per
    request; callers must `await registry.load_all(session)` once at the
    start of a request before using it.
    """

    def __init__(self):
        self._by_name: dict[str, ModuleMetadata] = {}

    async def load_all(self, session: AsyncSession) -> None:
        result = await session.execute(select(Module))
        for row in result.scalars():
            module = module_from_dict({**row.metadata_json, "name": row.name, "version": row.version})
            self._by_name[row.name] = module
            _cache[row.name] = module

    def get(self, name: str) -> ModuleMetadata:
        if name in self._by_name:
            return self._by_name[name]
        if name in _cache:
            return _cache[name]
        raise KeyError(f"unknown module: {name}")

    def all(self) -> dict[str, ModuleMetadata]:
        return {**_cache, **self._by_name}


def invalidate_cache(name: str | None = None) -> None:
    if name is None:
        _cache.clear()
    else:
        _cache.pop(name, None)
