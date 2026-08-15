from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/.env — anchored to the package location, not the process's
# working directory, since uvicorn/alembic/arq may all be launched from
# different cwds (repo root, apps/api, etc.).
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="METAFORGE_", env_file=_ENV_FILE)

    database_url: str = "postgresql+asyncpg://metaforge:metaforge@localhost:5432/metaforge"

    @property
    def sync_database_url(self) -> str:
        """Plain psycopg (sync) DSN for Alembic — migrations run over a sync
        connection so `write_and_apply` can be called from inside a request
        handler's already-running asyncio event loop without nesting
        `asyncio.run()` calls."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

    # App-level pool cap so FastAPI never opens more than ~20 live connections
    # concurrently, per the 4GB VM budget (max_connections=40 on Postgres side).
    db_pool_size: int = 10
    db_max_overflow: int = 10

    valkey_url: str = "redis://localhost:6379/0"
    session_secret: str = "change-me-in-.env"

    s3_endpoint_url: str | None = None
    s3_bucket: str = "metaforge"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None


settings = Settings()
