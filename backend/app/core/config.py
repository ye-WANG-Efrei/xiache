from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),   # works from both backend/ and project root
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://xiache:xiache@localhost:5432/xiache"

    # Storage
    STORAGE_PATH: str = "./data/artifacts"

    # Embedding (OpenAI-compatible)
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_API_BASE: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Security
    SECRET_KEY: str = "change-me-in-production-please-use-a-strong-random-key"

    # Dev mode — accept the literal string "dev-key-for-testing"
    XIACHE_DEV_MODE: bool = False
    DEV_API_KEY: str = "dev-key-for-testing"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Pagination
    DEFAULT_PAGE_LIMIT: int = 50
    MAX_PAGE_LIMIT: int = 500

    # Evolution workflow
    AUTO_ACCEPT_THRESHOLD: float = 0.6

    # LLM for auto-evolution (OpenAI-compatible)
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"

    # Auto-evolver quality thresholds
    AUTOEVO_MIN_SELECTIONS: int = 5      # minimum runs before evaluation
    AUTOEVO_FALLBACK_RATE: float = 0.40  # trigger if fallback_rate exceeds this
    AUTOEVO_COMPLETION_RATE: float = 0.35 # trigger if completion_rate below this


@lru_cache
def get_settings() -> Settings:
    return Settings()
