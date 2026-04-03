from __future__ import annotations

import hashlib
import io
import uuid
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_auth
from app.core.database import get_db
from app.core import storage
from app.models.db import Artifact
from app.schemas.api import ArtifactStats, StageArtifactResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/stage", response_model=StageArtifactResponse, status_code=status.HTTP_200_OK)
async def stage_artifact(
    files: list[UploadFile] = File(...),
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> StageArtifactResponse:
    """Accept multipart file upload(s), package into a ZIP, store on disk,
    and register a new Artifact row in the database.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one file is required",
        )

    # Build ZIP in-memory
    zip_buffer = io.BytesIO()
    file_names: list[str] = []
    total_size = 0

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for upload in files:
            content = await upload.read()
            filename = upload.filename or "unknown"
            zf.writestr(filename, content)
            file_names.append(filename)
            total_size += len(content)

    zip_bytes = zip_buffer.getvalue()
    fingerprint = hashlib.sha256(zip_bytes).hexdigest()
    artifact_id = str(uuid.uuid4())

    # Persist to filesystem
    await storage.save_artifact(artifact_id, zip_bytes)

    # Persist to database
    artifact = Artifact(
        id=artifact_id,
        file_count=len(files),
        file_names=file_names,
        content_fingerprint=fingerprint,
        created_at=datetime.now(timezone.utc),
        created_by=owner,
    )
    db.add(artifact)
    await db.flush()

    return StageArtifactResponse(
        artifact_id=artifact_id,
        stats=ArtifactStats(file_count=len(files), total_size=total_size),
    )
