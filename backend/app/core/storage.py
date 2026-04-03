from __future__ import annotations

import os
from pathlib import Path

import aiofiles

from app.core.config import get_settings

settings = get_settings()


def _artifact_path(artifact_id: str) -> Path:
    storage = Path(settings.STORAGE_PATH)
    # Shard by first two chars of the UUID to avoid huge flat directories
    shard = artifact_id[:2]
    return storage / shard / f"{artifact_id}.zip"


def artifact_exists(artifact_id: str) -> bool:
    return _artifact_path(artifact_id).exists()


async def save_artifact(artifact_id: str, zip_bytes: bytes) -> Path:
    path = _artifact_path(artifact_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(zip_bytes)
    return path


async def load_artifact(artifact_id: str) -> bytes:
    path = _artifact_path(artifact_id)
    if not path.exists():
        raise FileNotFoundError(f"Artifact {artifact_id} not found at {path}")
    async with aiofiles.open(path, "rb") as f:
        return await f.read()


def delete_artifact(artifact_id: str) -> bool:
    path = _artifact_path(artifact_id)
    if path.exists():
        os.remove(path)
        return True
    return False
