"""Loads seeds/modules_seed.json into the `modules` table — the metadata
registry every dynamic biz_* table's UI/API surface is driven from.

No migration populates this table (module definitions have always been
built up interactively through the builder, never captured as seed data)
so a fresh deploy has every physical biz_* table but zero module
definitions, and the app looks empty ("No modules yet") despite the
schema being fully migrated. Run once after `alembic upgrade head` on a
freshly deployed database:

    .venv/bin/python seeds/load_modules.py
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, "src")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from metaforge_api.infrastructure.models import Module
from metaforge_api.infrastructure.settings import settings

SEED_FILE = Path(__file__).parent / "modules_seed.json"


async def main() -> None:
    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        existing = {r.name for r in (await session.execute(select(Module.name))).scalars().all()}
        created = 0
        for row in rows:
            if row["name"] in existing:
                continue
            session.add(
                Module(
                    id=uuid.UUID(row["id"]),
                    name=row["name"],
                    metadata_json=row["metadata_json"],
                    version=row["version"],
                )
            )
            created += 1
        await session.commit()
        print(f"loaded {created} new modules ({len(rows) - created} already present, skipped)")
    await engine.dispose()


asyncio.run(main())
