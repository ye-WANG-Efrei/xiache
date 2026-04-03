from __future__ import annotations

import hashlib

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.db import ApiKey

settings = get_settings()
_bearer = HTTPBearer(auto_error=True)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Return the owner string for the authenticated API key.

    In dev mode (XIACHE_DEV_MODE=true) the literal DEV_API_KEY value
    is accepted without a database lookup.
    """
    raw_key = credentials.credentials

    if settings.XIACHE_DEV_MODE and raw_key == settings.DEV_API_KEY:
        return "dev"

    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key.owner
