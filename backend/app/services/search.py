from __future__ import annotations

import math
from typing import Any, Optional

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer."""
    return text.lower().split()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_records(
    query: str,
    candidates: list[dict[str, Any]],
    query_embedding: Optional[list[float]] = None,
    limit: int = 20,
    bm25_weight: float = 0.4,
    vector_weight: float = 0.6,
) -> list[dict[str, Any]]:
    """Hybrid BM25 + cosine similarity search over *candidates*.

    Each candidate dict must have at minimum:
        record_id, name, description, tags (list[str]), embedding (list[float] | None)

    Returns a ranked list of candidates (up to *limit*).
    """
    if not candidates:
        return []

    # Build corpus for BM25
    corpus_texts = [
        _tokenize(f"{c['name']} {c['description']} {' '.join(c.get('tags', []))}")
        for c in candidates
    ]
    query_tokens = _tokenize(query)

    bm25 = BM25Okapi(corpus_texts)
    bm25_scores = bm25.get_scores(query_tokens)

    # Normalize BM25 scores to [0, 1]
    bm25_max = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
    bm25_norm = [s / bm25_max for s in bm25_scores]

    # Vector scores
    has_vectors = (
        query_embedding is not None
        and any(c.get("embedding") for c in candidates)
    )
    if has_vectors:
        vector_scores = [
            _cosine_similarity(query_embedding, c.get("embedding") or [])
            for c in candidates
        ]
        combined = [
            bm25_weight * b + vector_weight * v
            for b, v in zip(bm25_norm, vector_scores)
        ]
    else:
        combined = bm25_norm

    # Sort and return top-k
    ranked = sorted(
        zip(combined, candidates),
        key=lambda x: x[0],
        reverse=True,
    )
    return [c for _, c in ranked[:limit]]
