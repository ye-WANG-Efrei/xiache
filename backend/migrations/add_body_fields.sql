-- Migration: remove ZIP dependency, store skill body directly in DB
-- Run after: add_skill_structured_fields.sql

-- Add body column to skill_records
ALTER TABLE skill_records
    ADD COLUMN IF NOT EXISTS body TEXT NOT NULL DEFAULT '';

-- Make artifact_id nullable (existing rows keep their value; new rows won't need it)
ALTER TABLE skill_records
    ALTER COLUMN artifact_id DROP NOT NULL;

-- Add proposed_body to skill_evolutions
ALTER TABLE skill_evolutions
    ADD COLUMN IF NOT EXISTS proposed_body TEXT NOT NULL DEFAULT '';

-- Make artifact_id nullable in evolutions too
ALTER TABLE skill_evolutions
    ALTER COLUMN artifact_id DROP NOT NULL;

-- Update FTS index to also cover body
DROP INDEX IF EXISTS idx_skill_records_fts;
CREATE INDEX IF NOT EXISTS idx_skill_records_fts
    ON skill_records USING GIN(
        to_tsvector('english', name || ' ' || description || ' ' || body)
    );
