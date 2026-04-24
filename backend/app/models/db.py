from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CategoryPrototype(Base):
    __tablename__ = "category_prototypes"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)   # category slug, e.g. "finance"
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    skill_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SkillRecord(Base):
    __tablename__ = "skill_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)   # UUID — backend-generated
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)  # user-supplied record_id
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    origin: Mapped[str] = mapped_column(String(64), nullable=False)
    visibility: Mapped[str] = mapped_column(String(64), nullable=False, default="public")
    level: Mapped[str] = mapped_column(String(64), nullable=False, default="tool_guide")
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="1.0.0")
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    input_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Quality counters — updated on every OpenSpace execution ingest
    total_selections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_applied: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_completions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_fallbacks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    children: Mapped[list["SkillLineage"]] = relationship(
        "SkillLineage",
        foreign_keys="SkillLineage.parent_slug",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parents: Mapped[list["SkillLineage"]] = relationship(
        "SkillLineage",
        foreign_keys="SkillLineage.child_slug",
        back_populates="child",
        cascade="all, delete-orphan",
    )


class SkillLineage(Base):
    __tablename__ = "skill_lineage"
    __table_args__ = (
        UniqueConstraint("child_slug", "parent_slug", name="uq_lineage_child_parent"),
    )

    child_slug: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("skill_records.slug", ondelete="CASCADE"),
        primary_key=True,
    )
    parent_slug: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("skill_records.slug", ondelete="CASCADE"),
        primary_key=True,
    )

    child: Mapped["SkillRecord"] = relationship(
        "SkillRecord", foreign_keys=[child_slug], back_populates="parents"
    )
    parent: Mapped["SkillRecord"] = relationship(
        "SkillRecord", foreign_keys=[parent_slug], back_populates="children"
    )


class SkillEvolution(Base):
    __tablename__ = "skill_evolutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    # Slugs stored here (not UUIDs) so API responses are human-readable without joins
    parent_skill_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    candidate_skill_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    result_record_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    origin: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    proposed_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    proposed_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    proposed_body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proposed_by: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evaluation_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    auto_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Store slug for human-readable audit trail (no FK — skill may be deleted/renamed)
    skill_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running", index=True)
    executor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="reasoning")
    target_env: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    called_by: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
