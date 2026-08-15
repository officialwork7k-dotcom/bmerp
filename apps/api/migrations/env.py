from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from metaforge_api.infrastructure.db import Base
from metaforge_api.infrastructure.settings import settings

# Import framework registry models so they're registered on Base.metadata
# for autogenerate; dynamic business tables are managed by schema_sync, not
# autogenerate, since they don't have static ORM classes.
from metaforge_api.infrastructure import models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Plain sync engine — deliberately NOT the app's async engine. schema_sync
    # calls `alembic upgrade` from inside FastAPI request handlers, which
    # already have a running asyncio event loop; a sync connection here
    # avoids nesting a second `asyncio.run()` inside that loop.
    connectable = create_engine(settings.sync_database_url)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
