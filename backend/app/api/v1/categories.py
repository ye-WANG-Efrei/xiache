from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.api.v1.deps import require_auth
from app.core.database import get_db
from app.models.db import CategoryPrototype
from app.schemas.api import CategoryItem, CategoryListResponse

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse, summary="List all semantic categories")
async def list_categories(
    owner: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> CategoryListResponse:
    """Return all registered categories with their skill counts, ordered by skill count desc."""
    rows = (
        await db.execute(
            select(CategoryPrototype).order_by(CategoryPrototype.skill_count.desc())
        )
    ).scalars().all()

    items = [
        CategoryItem(
            id=r.id,
            label=r.label,
            skill_count=r.skill_count,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return CategoryListResponse(items=items, count=len(items))
