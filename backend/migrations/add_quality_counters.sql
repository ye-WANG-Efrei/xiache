-- Migration: add quality counters to skill_records
-- Mirrors OpenSpace's SkillRecord counters for execution-driven quality tracking.

ALTER TABLE skill_records
    ADD COLUMN IF NOT EXISTS total_selections  INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_applied     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_completions INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_fallbacks   INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_skill_records_selections
    ON skill_records (total_selections);
