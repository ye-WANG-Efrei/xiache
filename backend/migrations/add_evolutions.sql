-- Migration: add skill_evolutions table
-- Adds the PR-like workflow for skill evolution proposals.

CREATE TABLE IF NOT EXISTS skill_evolutions (
    id               VARCHAR(36)  PRIMARY KEY,          -- UUID
    artifact_id      VARCHAR(36)  NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    parent_skill_id  VARCHAR(255) REFERENCES skill_records(id) ON DELETE SET NULL,
    origin           VARCHAR(64)  NOT NULL,              -- fixed | derived | captured
    status           VARCHAR(32)  NOT NULL DEFAULT 'pending',  -- pending | evaluating | accepted | rejected
    proposed_name    VARCHAR(255) NOT NULL DEFAULT '',   -- extracted from SKILL.md
    proposed_desc    TEXT         NOT NULL DEFAULT '',
    change_summary   TEXT         NOT NULL DEFAULT '',
    content_diff     TEXT,
    proposed_by      VARCHAR(255) NOT NULL DEFAULT '',   -- agent:xxx or api-key owner
    tags             JSONB        NOT NULL DEFAULT '[]',
    proposed_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    evaluated_at     TIMESTAMPTZ,
    result_record_id VARCHAR(255) REFERENCES skill_records(id) ON DELETE SET NULL,
    evaluation_notes TEXT         NOT NULL DEFAULT '',   -- feedback returned to agent
    quality_score    FLOAT,
    auto_accepted    BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_evolutions_status        ON skill_evolutions (status);
CREATE INDEX IF NOT EXISTS idx_evolutions_parent        ON skill_evolutions (parent_skill_id);
CREATE INDEX IF NOT EXISTS idx_evolutions_proposed_at   ON skill_evolutions (proposed_at DESC);
CREATE INDEX IF NOT EXISTS idx_evolutions_proposed_by   ON skill_evolutions (proposed_by);
