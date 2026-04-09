"""Integration-only fixtures — requires Docker + PostgreSQL container."""
from __future__ import annotations

import asyncio
import re

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Skip entire integration suite if Docker is unavailable
def _docker_available() -> bool:
    try:
        import docker
        docker.from_env().ping()
        return True
    except Exception:
        return False


if not _docker_available():
    pytest.skip("Docker not available — skipping integration tests",
                allow_module_level=True)

from testcontainers.postgres import PostgresContainer

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_engine(postgres):
    raw_url = postgres.get_connection_url()
    url = re.sub(r"^postgresql(\+\w+)?://", "postgresql+asyncpg://", raw_url)
    engine = create_async_engine(url, echo=False, pool_pre_ping=True)

    async def _setup():
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_setup())
    yield engine
    asyncio.get_event_loop().run_until_complete(engine.dispose())


@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_engine):
    """Truncate all tables after each integration test."""
    yield
    async with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def http_client(db_engine, tmp_path, monkeypatch):
    import app.core.storage as storage_module
    monkeypatch.setattr(storage_module.settings, "STORAGE_PATH",
                        str(tmp_path / "artifacts"))
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)

    test_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async def override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
