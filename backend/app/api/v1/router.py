from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import artifacts, evolutions, ingest, records, runs, search
from app.api.v1.health import router as health_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router)
router.include_router(artifacts.router)
router.include_router(records.router)
router.include_router(search.router)
router.include_router(evolutions.router)
router.include_router(runs.router)
router.include_router(ingest.router)
