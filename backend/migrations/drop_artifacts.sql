-- Migration: remove artifact_id from skill_records and skill_evolutions, drop artifacts table
-- Run after: add_slug_uuid_pk.sql

ALTER TABLE skill_records    DROP COLUMN IF EXISTS artifact_id;
ALTER TABLE skill_evolutions DROP COLUMN IF EXISTS artifact_id;

-- artifacts table is now fully unused; drop it
DROP TABLE IF EXISTS artifacts;
