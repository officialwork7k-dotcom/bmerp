from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from metaforge_api.infrastructure.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    """Commits at request teardown, not just on explicit `session.commit()`
    calls inside handlers.

    SQLAlchemy 2.0 async sessions "autobegin" a transaction on first use —
    e.g. the module-registry SELECT that every request already does before
    a repository write ever runs. That means a repository write later sees
    `session.in_transaction() == True` and opens a SAVEPOINT
    (`begin_nested()`) instead of a real transaction, and releasing a
    savepoint is not a commit: without this, the enclosing autobegun
    transaction is silently rolled back when the session closes, and writes
    that returned 200 with a full row never actually land in Postgres.
    """
    async with async_session_factory() as session:
        yield session
        await session.commit()
