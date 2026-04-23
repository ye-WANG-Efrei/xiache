from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import evolutions, ingest, runs, search, skills
from app.api.v1.health import router as health_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router)
router.include_router(skills.router)
router.include_router(search.router)
router.include_router(evolutions.router)
router.include_router(runs.router)
router.include_router(ingest.router)
