-- xiache initial schema
-- Run this against a PostgreSQL 16+ database with the pgvector extension available.

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id          SERIAL PRIMARY KEY,
    key_hash    CHAR(64)     NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    owner       VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);

-- Artifacts (staged ZIP files)
CREATE TABLE IF NOT EXISTS artifacts (
    id                   VARCHAR(36)  PRIMARY KEY,         -- UUID
    file_count           INTEGER      NOT NULL,
    file_names           JSONB        NOT NULL DEFAULT '[]',
    content_fingerprint  CHAR(64)     NOT NULL,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by           VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_fingerprint ON artifacts (content_fingerprint);

-- Skill Records
CREATE TABLE IF NOT EXISTS skill_records (
    id                   VARCHAR(255) PRIMARY KEY,
    artifact_id          VARCHAR(36)  NOT NULL REFERENCES artifacts (id) ON DELETE RESTRICT,
    name                 VARCHAR(255) NOT NULL,
    description          TEXT         NOT NULL DEFAULT '',
    origin               VARCHAR(64)  NOT NULL,
    visibility           VARCHAR(64)  NOT NULL DEFAULT 'public',
    level                VARCHAR(64)  NOT NULL DEFAULT 'tool_guide',
    tags                 JSONB        NOT NULL DEFAULT '[]',
    created_by           VARCHAR(255) NOT NULL DEFAULT '',
    change_summary       TEXT         NOT NULL DEFAULT '',
    content_diff         TEXT,
    content_fingerprint  CHAR(64)     NOT NULL,
    embedding            vector(1536),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_records_name        ON skill_records (name);
CREATE INDEX IF NOT EXISTS idx_skill_records_fingerprint ON skill_records (content_fingerprint);
CREATE INDEX IF NOT EXISTS idx_skill_records_artifact    ON skill_records (artifact_id);
CREATE INDEX IF NOT EXISTS idx_skill_records_created_at  ON skill_records (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_records_visibility  ON skill_records (visibility);

-- Vector index for approximate nearest-neighbour search (cosine)
CREATE INDEX IF NOT EXISTS idx_skill_records_embedding
    ON skill_records USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Full-text search index (GIN on tsvector of name + description)
CREATE INDEX IF NOT EXISTS idx_skill_records_fts
    ON skill_records USING GIN(to_tsvector('english', name || ' ' || description));

-- Skill Lineage (DAG edges)
CREATE TABLE IF NOT EXISTS skill_lineage (
    child_id   VARCHAR(255) NOT NULL REFERENCES skill_records (id) ON DELETE CASCADE,
    parent_id  VARCHAR(255) NOT NULL REFERENCES skill_records (id) ON DELETE CASCADE,
    PRIMARY KEY (child_id, parent_id)
);

CREATE INDEX IF NOT EXISTS idx_lineage_parent ON skill_lineage (parent_id);
CREATE INDEX IF NOT EXISTS idx_lineage_child  ON skill_lineage (child_id);

-- Dev seed: insert a dev API key (SHA256 of "dev-key-for-testing")
-- Only useful when XIACHE_DEV_MODE=false but you still want a DB key for testing.
-- SHA256("dev-key-for-testing") = 9e4a3a6e77f9e3cd4cf6e8b3fecf4d78d4e9a847afac9e23b21d4bfc3c1a3c98
-- (Commented out — enable XIACHE_DEV_MODE=true in .env instead for local dev)
-- INSERT INTO api_keys (key_hash, name, owner, is_active)
-- VALUES ('9e4a3a6e77f9e3cd4cf6e8b3fecf4d78d4e9a847afac9e23b21d4bfc3c1a3c98', 'dev-key', 'dev', true)
-- ON CONFLICT (key_hash) DO NOTHING;
