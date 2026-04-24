-- Category prototypes: one representative embedding per category.
-- The embedding is the incremental centroid of all skills in that category.
CREATE TABLE IF NOT EXISTS category_prototypes (
    id          VARCHAR(255) PRIMARY KEY,       -- category slug, e.g. "finance"
    label       VARCHAR(255) NOT NULL DEFAULT '',
    skill_count INTEGER      NOT NULL DEFAULT 0,
    embedding   VECTOR(1536),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_category_prototypes_embedding
    ON category_prototypes USING hnsw (embedding vector_cosine_ops);

-- Add category column to skill_records (nullable — existing rows stay uncategorised)
ALTER TABLE skill_records
    ADD COLUMN IF NOT EXISTS category VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_skill_records_category
    ON skill_records (category);
