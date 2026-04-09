from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_tables

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("xiache starting up — creating database tables…")
    await create_tables()
    logger.info("Database tables ready.")
    yield
    logger.info("xiache shutting down.")


app = FastAPI(
    title="xiache",
    description=(
        "Agent-native open source platform. "
        "Store, version, discover, and evolve AI agent skills."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins in dev; tighten via CORS_ORIGINS env var in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
from app.api.v1.router import router as api_v1_router  # noqa: E402

app.include_router(api_v1_router)


# Convenience top-level health (mirrors /api/v1/health)
@app.get("/health", tags=["health"], include_in_schema=False)
async def root_health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
