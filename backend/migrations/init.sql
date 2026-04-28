-- Xiache full schema — fresh install (PostgreSQL 16+ with pgvector)
-- This file is the single source of truth for a new database.
-- Existing databases: keep running individual migration files in order.

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
-- Category Prototypes  (one representative embedding per category)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS category_prototypes (
    id          VARCHAR(255) PRIMARY KEY,       -- category slug, e.g. "finance"
    label       VARCHAR(255) NOT NULL DEFAULT '',
    skill_count INTEGER      NOT NULL DEFAULT 0,
    embedding   VECTOR(2048),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Vector index created in 03_indexes.sql after seed data is loaded

-- ---------------------------------------------------------------------------
-- Skill Records  (versioned, accepted skills)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_records (
    id                   VARCHAR(36)  PRIMARY KEY,   -- UUID, backend-generated
    slug                 VARCHAR(255) NOT NULL UNIQUE,  -- human-readable identifier
    category             VARCHAR(255),
    name                 VARCHAR(255) NOT NULL,
    description          TEXT         NOT NULL DEFAULT '',
    body                 TEXT         NOT NULL DEFAULT '',
    version              VARCHAR(64)  NOT NULL DEFAULT '1.0.0',
    origin               VARCHAR(64)  NOT NULL,
    visibility           VARCHAR(64)  NOT NULL DEFAULT 'public',
    level                VARCHAR(64)  NOT NULL DEFAULT 'tool_guide',
    tags                 JSONB        NOT NULL DEFAULT '[]',
    input_schema         JSONB        NOT NULL DEFAULT '{}',
    output_schema        JSONB        NOT NULL DEFAULT '{}',
    created_by           VARCHAR(255) NOT NULL DEFAULT '',
    change_summary       TEXT         NOT NULL DEFAULT '',
    content_diff         TEXT,
    content_fingerprint  CHAR(64)     NOT NULL,
    embedding            VECTOR(2048),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    total_selections     INTEGER      NOT NULL DEFAULT 0,
    total_applied        INTEGER      NOT NULL DEFAULT 0,
    total_completions    INTEGER      NOT NULL DEFAULT 0,
    total_fallbacks      INTEGER      NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_records_slug       ON skill_records (slug);
CREATE INDEX        IF NOT EXISTS idx_skill_records_name       ON skill_records (name);
CREATE INDEX        IF NOT EXISTS idx_skill_records_fingerprint ON skill_records (content_fingerprint);
CREATE INDEX        IF NOT EXISTS idx_skill_records_created_at ON skill_records (created_at DESC);
CREATE INDEX        IF NOT EXISTS idx_skill_records_visibility ON skill_records (visibility);
CREATE INDEX        IF NOT EXISTS idx_skill_records_category   ON skill_records (category);

-- Vector index created in 03_indexes.sql after seed data is loaded

CREATE INDEX IF NOT EXISTS idx_skill_records_fts
    ON skill_records USING GIN(to_tsvector('english', name || ' ' || description || ' ' || body));

-- ---------------------------------------------------------------------------
-- Skill Lineage  (DAG: which skill evolved from which)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_lineage (
    child_slug   VARCHAR(255) NOT NULL REFERENCES skill_records(slug) ON DELETE CASCADE,
    parent_slug  VARCHAR(255) NOT NULL REFERENCES skill_records(slug) ON DELETE CASCADE,
    PRIMARY KEY (child_slug, parent_slug),
    CONSTRAINT uq_lineage_child_parent UNIQUE (child_slug, parent_slug)
);

CREATE INDEX IF NOT EXISTS idx_lineage_parent ON skill_lineage (parent_slug);
CREATE INDEX IF NOT EXISTS idx_lineage_child  ON skill_lineage (child_slug);

-- ---------------------------------------------------------------------------
-- Skill Evolutions  (PR-like proposals awaiting review)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_evolutions (
    id                  VARCHAR(36)  PRIMARY KEY,
    parent_skill_id     VARCHAR(255),
    candidate_skill_id  VARCHAR(255),
    result_record_id    VARCHAR(255),
    origin              VARCHAR(64)  NOT NULL,
    status              VARCHAR(32)  NOT NULL DEFAULT 'pending',
    proposed_name       VARCHAR(255) NOT NULL DEFAULT '',
    proposed_desc       TEXT         NOT NULL DEFAULT '',
    proposed_body       TEXT         NOT NULL DEFAULT '',
    change_summary      TEXT         NOT NULL DEFAULT '',
    content_diff        TEXT,
    proposed_by         VARCHAR(255) NOT NULL DEFAULT '',
    tags                JSONB        NOT NULL DEFAULT '[]',
    proposed_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    evaluated_at        TIMESTAMPTZ,
    evaluation_notes    TEXT         NOT NULL DEFAULT '',
    quality_score       FLOAT,
    auto_accepted       BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_evolutions_status       ON skill_evolutions (status);
CREATE INDEX IF NOT EXISTS idx_evolutions_parent       ON skill_evolutions (parent_skill_id);
CREATE INDEX IF NOT EXISTS idx_evolutions_candidate    ON skill_evolutions (candidate_skill_id);
CREATE INDEX IF NOT EXISTS idx_evolutions_proposed_at  ON skill_evolutions (proposed_at DESC);
CREATE INDEX IF NOT EXISTS idx_evolutions_proposed_by  ON skill_evolutions (proposed_by);

-- ---------------------------------------------------------------------------
-- Execution Runs  (audit log for every skill invocation)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS execution_runs (
    id             VARCHAR(36)  PRIMARY KEY,
    skill_id       VARCHAR(255),
    task           TEXT         NOT NULL DEFAULT '',
    status         VARCHAR(32)  NOT NULL DEFAULT 'running',
    executor_type  VARCHAR(32)  NOT NULL DEFAULT 'reasoning',
    target_env     JSONB        NOT NULL DEFAULT '{}',
    started_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ,
    result         TEXT,
    error          TEXT,
    run_log        TEXT,
    called_by      VARCHAR(255) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_runs_skill_id   ON execution_runs (skill_id);
CREATE INDEX IF NOT EXISTS idx_runs_status     ON execution_runs (status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON execution_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_called_by  ON execution_runs (called_by);
