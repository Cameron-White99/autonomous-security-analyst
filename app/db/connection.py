"""Async connection to Neon PostgreSQL via asyncpg directly.

When DATABASE_URL is unset (or connection fails) the pool stays None and
repositories fall back to in-memory storage.
"""

import json
import logging
from pathlib import Path

import asyncpg

from app.config import get_settings

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

_pool: asyncpg.Pool | None = None


async def _init_conn(conn: asyncpg.Connection) -> None:
    """Register JSONB codec so Python dicts round-trip transparently."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def init_db() -> None:
    global _pool
    settings = get_settings()
    if not settings.database_url:
        logger.warning("DATABASE_URL not set — using in-memory storage (demo only)")
        return

    # asyncpg expects postgresql:// not postgresql+asyncpg://
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        _pool = await asyncpg.create_pool(url, init=_init_conn)
        async with _pool.acquire() as conn:
            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                sql = migration.read_text()
                for statement in (s.strip() for s in sql.split(";")):
                    if statement:
                        await conn.execute(statement)
        logger.info("Database schema ready")
    except Exception as exc:
        logger.warning("Database init failed (%s) — falling back to in-memory storage", exc)
        _pool = None


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool | None:
    return _pool
