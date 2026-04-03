from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_auth
from app.core.database import get_db
from app.models.db import ExecutionRun

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    skill_id: Optional[str] = None
    task: str
    executor_type: str = "reasoning"
    target_env: dict = {}
    context: dict = {}


class UpdateRunRequest(BaseModel):
    status: str           # success | failed
    result: Optional[str] = None
    error: Optional[str] = None
    run_log: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    skill_id: Optional[str]
    task: str
    status: str
    executor_type: str
    target_env: dict
    started_at: datetime
    completed_at: Optional[datetime]
    result: Optional[str]
    error: Optional[str]
    run_log: Optional[str]
    called_by: str


def _to_response(run: ExecutionRun) -> RunResponse:
    return RunResponse(
        run_id=run.id,
        skill_id=run.skill_id,
        task=run.task,
        status=run.status,
        executor_type=run.executor_type,
        target_env=run.target_env or {},
        started_at=run.started_at,
        completed_at=run.completed_at,
        result=run.result,
        error=run.error,
        run_log=run.run_log,
        called_by=run.called_by,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RunResponse)
async def create_run(
    body: CreateRunRequest,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    run = ExecutionRun(
        id=str(uuid.uuid4()),
        skill_id=body.skill_id,
        task=body.task,
        status="running",
        executor_type=body.executor_type,
        target_env=body.target_env,
        started_at=datetime.now(timezone.utc),
        called_by=owner,
    )
    db.add(run)
    await db.flush()
    return _to_response(run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return _to_response(run)


@router.patch("/{run_id}", response_model=RunResponse)
async def update_run(
    run_id: str,
    body: UpdateRunRequest,
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Close a run with success or failure."""
    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    if run.status != "running":
        raise HTTPException(status_code=409, detail="Run is already closed")

    run.status = body.status
    run.completed_at = datetime.now(timezone.utc)
    if body.result is not None:
        run.result = body.result
    if body.error is not None:
        run.error = body.error
    if body.run_log is not None:
        run.run_log = body.run_log

    db.add(run)
    await db.flush()
    return _to_response(run)
