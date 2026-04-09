-- Migration: add execution_runs table
-- Tracks every time a skill was invoked: who called it, what happened, result.

CREATE TABLE IF NOT EXISTS execution_runs (
    id             VARCHAR(36)  PRIMARY KEY,                 -- UUID
    skill_id       VARCHAR(255) REFERENCES skill_records(id) ON DELETE SET NULL,
    task           TEXT         NOT NULL DEFAULT '',         -- what the caller asked for
    status         VARCHAR(32)  NOT NULL DEFAULT 'running',  -- running | done | failed
    executor_type  VARCHAR(32)  NOT NULL DEFAULT 'reasoning',-- reasoning | digital | physical
    target_env     JSONB        NOT NULL DEFAULT '{}',       -- e.g. {"platform": "esp32"}
    started_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ,
    result         TEXT,
    error          TEXT,
    run_log        TEXT,
    called_by      VARCHAR(255) NOT NULL DEFAULT ''          -- agent:xxx or api-key owner
);

CREATE INDEX IF NOT EXISTS idx_runs_skill_id    ON execution_runs (skill_id);
CREATE INDEX IF NOT EXISTS idx_runs_status      ON execution_runs (status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at  ON execution_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_called_by   ON execution_runs (called_by);
