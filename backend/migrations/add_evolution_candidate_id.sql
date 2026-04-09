-- Migration: add candidate_skill_id to skill_evolutions
-- The desired record_id when this evolution is accepted (e.g. "blink_led_v2").
-- Falls back to "evo:<uuid>" if NULL.

ALTER TABLE skill_evolutions
    ADD COLUMN IF NOT EXISTS candidate_skill_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_evolutions_candidate ON skill_evolutions (candidate_skill_id);
