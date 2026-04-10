from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Evolutions
# ---------------------------------------------------------------------------


class ProposeEvolutionRequest(BaseModel):
    name: str
    description: str = ""
    body: str = ""
    parent_skill_id: Optional[str] = None   # null for brand-new skills
    candidate_skill_id: Optional[str] = None # desired record_id on accept, e.g. "blink_led_v2"
    origin: str  # fixed | derived | captured
    change_summary: str = ""
    content_diff: Optional[str] = None
    tags: list[str] = []


class EvaluationResult(BaseModel):
    passed: bool
    quality_score: float        # 0.0 – 1.0
    notes: str                  # human/agent-readable feedback
    checks: dict[str, bool]     # individual check results


class EvolutionResponse(BaseModel):
    evolution_id: str
    status: str                      # pending | evaluating | accepted | rejected
    proposed_name: str
    proposed_desc: str
    parent_skill_id: Optional[str]
    candidate_skill_id: Optional[str]  # desired record_id; becomes result_record_id on accept
    origin: str
    proposed_by: str
    proposed_at: datetime
    evaluated_at: Optional[datetime]
    evaluation: Optional[EvaluationResult]
    result_record_id: Optional[str]    # set when accepted
    change_summary: str
    tags: list[str]
    auto_accepted: bool


# ---------------------------------------------------------------------------
# Records — request
# ---------------------------------------------------------------------------


class CreateRecordRequest(BaseModel):
    record_id: str = Field(..., description="Unique identifier for this skill record")
    name: str = Field(..., description="Skill name")
    description: str = Field("", description="One-line description of what the skill does")
    body: str = Field("", description="Skill body / instructions (Markdown)")
    origin: str = Field(..., description="imported | captured | derived | fixed")
    visibility: str = Field("public", description="public | group_only")
    parent_skill_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    level: str = Field("tool_guide", description="workflow | tool_guide | reference")
    version: str = Field("1.0.0")
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = Field(None)
    change_summary: Optional[str] = Field(None)
    content_diff: Optional[str] = Field(None)


# ---------------------------------------------------------------------------
# Records — response
# ---------------------------------------------------------------------------


class RecordResponse(BaseModel):
    record_id: str
    artifact_id: Optional[str]
    artifact_ref: str
    name: str
    description: str
    body: str
    version: str
    origin: str
    visibility: str
    level: str
    tags: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    created_by: str
    change_summary: str
    content_diff: Optional[str]
    content_fingerprint: str
    parent_skill_ids: list[str]
    created_at: datetime
    embedding: Optional[list[float]] = None

    model_config = {"from_attributes": True}


class RecordMetadataItem(BaseModel):
    record_id: str
    artifact_id: Optional[str]
    artifact_ref: str
    name: str
    description: str
    body: str
    version: str
    origin: str
    visibility: str
    level: str
    tags: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    created_by: str
    change_summary: str
    content_fingerprint: str
    parent_skill_ids: list[str]
    created_at: datetime
    embedding: Optional[list[float]] = None

    model_config = {"from_attributes": True}


class RecordMetadataResponse(BaseModel):
    items: list[RecordMetadataItem]
    has_more: bool
    next_cursor: Optional[str]
    total: int


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchResult(BaseModel):
    record_id: str
    name: str
    description: str
    origin: str
    visibility: str
    level: str
    tags: list[str]
    created_by: str
    created_at: datetime
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    count: int
    search_type: str  # "hybrid" | "fulltext"


# ---------------------------------------------------------------------------
# OpenSpace ingestion — mirrors ExecutionAnalysis from HKUDS/OpenSpace
# ---------------------------------------------------------------------------


class OpenSpaceSkillJudgment(BaseModel):
    skill_id: str
    skill_applied: bool
    note: str = Field("", max_length=500)  # capped to limit prompt injection surface


class OpenSpaceEvolutionSuggestion(BaseModel):
    type: str                          # fix | derived | captured
    target_skills: list[str] = []     # preferred multi-parent field
    target_skill: str = ""            # legacy single-skill field (fallback)
    category: Optional[str] = None
    direction: str = Field("", max_length=1000)

    def resolved_targets(self) -> list[str]:
        return self.target_skills or ([self.target_skill] if self.target_skill else [])


class OpenSpaceIngestionRequest(BaseModel):
    task_id: str
    timestamp: datetime
    task_completed: bool
    execution_note: str = Field("", max_length=500)  # capped to limit prompt injection surface
    tool_issues: list[str] = []
    skill_judgments: list[OpenSpaceSkillJudgment] = []
    evolution_suggestions: list[OpenSpaceEvolutionSuggestion] = []
    analyzed_by: str = ""
    analyzed_at: datetime


class IngestionResult(BaseModel):
    task_id: str
    judgments_processed: int
    counters_updated: list[str]        # skill_ids whose counters changed
    evolutions_triggered: list[str]    # skill_ids that crossed threshold → auto-evo queued


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    existing_record_id: Optional[str] = None
    fingerprint: Optional[str] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    database: str = "unknown"
