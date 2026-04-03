from __future__ import annotations

import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


async def generate_embedding(text: str) -> Optional[list[float]]:
    """Generate a vector embedding for *text*.

    Uses the OpenAI-compatible API if EMBEDDING_API_KEY is configured,
    otherwise returns None (embedding-less mode).
    """
    if not settings.EMBEDDING_API_KEY:
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_API_BASE,  # None → default OpenAI endpoint
        )
        response = await client.embeddings.create(
            input=text,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding
    except Exception as exc:
        logger.warning("Embedding generation failed: %s", exc)
        return None


def build_embedding_text(name: str, description: str, tags: list[str]) -> str:
    """Combine skill metadata into a single string for embedding."""
    parts = [name, description]
    if tags:
        parts.append("tags: " + ", ".join(tags))
    return " | ".join(p for p in parts if p)
