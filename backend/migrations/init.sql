-- Xiache full schema (run on a fresh PostgreSQL 16+ with pgvector)
-- Apply order for existing DBs:
--   1. init.sql  (this file — idempotent, safe to re-run)
--   2. add_evolutions.sql
--   3. add_execution_runs.sql
--   4. add_skill_structured_fields.sql

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- API Keys
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_keys (
    id          SERIAL       PRIMARY KEY,
    key_hash    CHAR(64)     NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    owner       VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);

-- ---------------------------------------------------------------------------
-- Artifacts  (legacy staging table — kept for backward compatibility only)
-- New records no longer require an artifact_id; body is stored directly in skill_records.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS artifacts (
    id                   VARCHAR(36)  PRIMARY KEY,   -- UUID
    file_count           INTEGER      NOT NULL,
    file_names           JSONB        NOT NULL DEFAULT '[]',
    content_fingerprint  CHAR(64)     NOT NULL,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by           VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_fingerprint ON artifacts (content_fingerprint);

-- ---------------------------------------------------------------------------
-- Skill Records  (versioned, accepted skills — body stored directly in DB)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_records (
    id                   VARCHAR(255) PRIMARY KEY,   -- human-readable skill_id
    artifact_id          VARCHAR(36)  REFERENCES artifacts(id) ON DELETE RESTRICT,  -- nullable: legacy only
    name                 VARCHAR(255) NOT NULL,
    description          TEXT         NOT NULL DEFAULT '',
    body                 TEXT         NOT NULL DEFAULT '',
    version              VARCHAR(64)  NOT NULL DEFAULT '1.0.0',
    origin               VARCHAR(64)  NOT NULL,      -- imported | captured | derived | fixed
    visibility           VARCHAR(64)  NOT NULL DEFAULT 'public',
    level                VARCHAR(64)  NOT NULL DEFAULT 'tool_guide',
    tags                 JSONB        NOT NULL DEFAULT '[]',
    input_schema         JSONB        NOT NULL DEFAULT '{}',
    output_schema        JSONB        NOT NULL DEFAULT '{}',
    created_by           VARCHAR(255) NOT NULL DEFAULT '',
    change_summary       TEXT         NOT NULL DEFAULT '',
    content_diff         TEXT,
    content_fingerprint  CHAR(64)     NOT NULL,
    embedding            vector(1536),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    total_selections     INTEGER      NOT NULL DEFAULT 0,
    total_applied        INTEGER      NOT NULL DEFAULT 0,
    total_completions    INTEGER      NOT NULL DEFAULT 0,
    total_fallbacks      INTEGER      NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_skill_records_name        ON skill_records (name);
CREATE INDEX IF NOT EXISTS idx_skill_records_fingerprint ON skill_records (content_fingerprint);
CREATE INDEX IF NOT EXISTS idx_skill_records_artifact    ON skill_records (artifact_id);
CREATE INDEX IF NOT EXISTS idx_skill_records_created_at  ON skill_records (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_records_visibility  ON skill_records (visibility);

CREATE INDEX IF NOT EXISTS idx_skill_records_embedding
    ON skill_records USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_skill_records_fts
    ON skill_records USING GIN(to_tsvector('english', name || ' ' || description || ' ' || body));

-- ---------------------------------------------------------------------------
-- Skill Lineage  (DAG: which skill evolved from which)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_lineage (
    child_id   VARCHAR(255) NOT NULL REFERENCES skill_records(id) ON DELETE CASCADE,
    parent_id  VARCHAR(255) NOT NULL REFERENCES skill_records(id) ON DELETE CASCADE,
    PRIMARY KEY (child_id, parent_id)
);

CREATE INDEX IF NOT EXISTS idx_lineage_parent ON skill_lineage (parent_id);
CREATE INDEX IF NOT EXISTS idx_lineage_child  ON skill_lineage (child_id);

-- ---------------------------------------------------------------------------
-- Skill Evolutions  (PR-like proposals: new/changed skill awaiting review)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_evolutions (
    id                  VARCHAR(36)  PRIMARY KEY,        -- UUID
    artifact_id         VARCHAR(36)  REFERENCES artifacts(id) ON DELETE RESTRICT,  -- nullable: legacy only
    parent_skill_id     VARCHAR(255) REFERENCES skill_records(id) ON DELETE SET NULL,
    candidate_skill_id  VARCHAR(255),                   -- desired record_id on accept, e.g. "blink_led_v2"
    origin              VARCHAR(64)  NOT NULL,           -- fixed | derived | captured
    status              VARCHAR(32)  NOT NULL DEFAULT 'pending', -- pending | evaluating | accepted | rejected
    proposed_name       VARCHAR(255) NOT NULL DEFAULT '',
    proposed_desc       TEXT         NOT NULL DEFAULT '',
    proposed_body       TEXT         NOT NULL DEFAULT '',
    change_summary   TEXT         NOT NULL DEFAULT '',
    content_diff     TEXT,
    proposed_by      VARCHAR(255) NOT NULL DEFAULT '',  -- agent:xxx or api-key owner
    tags             JSONB        NOT NULL DEFAULT '[]',
    proposed_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    evaluated_at     TIMESTAMPTZ,
    result_record_id VARCHAR(255) REFERENCES skill_records(id) ON DELETE SET NULL,
    evaluation_notes TEXT         NOT NULL DEFAULT '',
    quality_score    FLOAT,
    auto_accepted    BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_evolutions_status       ON skill_evolutions (status);
CREATE INDEX IF NOT EXISTS idx_evolutions_parent       ON skill_evolutions (parent_skill_id);
CREATE INDEX IF NOT EXISTS idx_evolutions_candidate    ON skill_evolutions (candidate_skill_id);
CREATE INDEX IF NOT EXISTS idx_evolutions_proposed_at  ON skill_evolutions (proposed_at DESC);
CREATE INDEX IF NOT EXISTS idx_evolutions_proposed_by  ON skill_evolutions (proposed_by);

-- ---------------------------------------------------------------------------
-- Execution Runs  (every time a skill was invoked — audit log)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS execution_runs (
    id             VARCHAR(36)  PRIMARY KEY,           -- UUID
    skill_id       VARCHAR(255) REFERENCES skill_records(id) ON DELETE SET NULL,
    task           TEXT         NOT NULL DEFAULT '',   -- what the caller asked for
    status         VARCHAR(32)  NOT NULL DEFAULT 'running', -- running | done | failed
    executor_type  VARCHAR(32)  NOT NULL DEFAULT 'reasoning', -- reasoning | digital | physical
    target_env     JSONB        NOT NULL DEFAULT '{}', -- e.g. {"platform": "esp32"}
    started_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ,
    result         TEXT,
    error          TEXT,
    run_log        TEXT,
    called_by      VARCHAR(255) NOT NULL DEFAULT ''    -- agent:xxx or api-key owner
);

CREATE INDEX IF NOT EXISTS idx_runs_skill_id   ON execution_runs (skill_id);
CREATE INDEX IF NOT EXISTS idx_runs_status     ON execution_runs (status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON execution_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_called_by  ON execution_runs (called_by);
