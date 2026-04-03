from __future__ import annotations

import ssl
from collections.abc import AsyncGenerator
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()


def _build_engine_args(db_url: str) -> tuple[str, dict]:
    """Strip psycopg2-style SSL params and return (clean_url, connect_args)."""
    parsed = urlparse(db_url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    ssl_params = {"sslmode", "sslrootcert", "sslcert", "sslkey", "channel_binding"}
    needs_ssl = "sslmode" in params and params["sslmode"][0] in ("require", "verify-ca", "verify-full")

    clean_params = {k: v for k, v in params.items() if k not in ssl_params}
    clean_query = urlencode(clean_params, doseq=True)
    clean_url = urlunparse(parsed._replace(query=clean_query))

    connect_args: dict = {}
    if needs_ssl:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    return clean_url, connect_args


_db_url, _connect_args = _build_engine_args(settings.DATABASE_URL)

engine = create_async_engine(
    _db_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables (called at startup)."""
    # Import models so their metadata is registered
    from app.models import db as _  # noqa: F401

    async with engine.begin() as conn:
        # Ensure pgvector extension exists
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.run_sync(Base.metadata.create_all)
