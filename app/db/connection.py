"""Async connection to Neon PostgreSQL (asyncpg + SQLAlchemy async).

When DATABASE_URL is unset the engine stays None and the repositories fall
back to in-memory storage — useful for local demos without infrastructure.
"""

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import get_settings

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

engine: AsyncEngine | None = None


async def init_db() -> None:
    """Create the engine and apply schema migrations on startup."""
    global engine
    settings = get_settings()
    if not settings.database_url:
        logger.warning("DATABASE_URL not set — using in-memory storage (demo only)")
        return

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = migration.read_text()
            # asyncpg prepares statements individually — split the file
            for statement in (s.strip() for s in sql.split(";")):
                if statement:
                    await conn.exec_driver_sql(statement)
    logger.info("Database schema ready")


async def close_db() -> None:
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None


def get_engine() -> AsyncEngine | None:
    return engine
