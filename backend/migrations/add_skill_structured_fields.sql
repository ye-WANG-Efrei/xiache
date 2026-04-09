-- Migration: add version, input_schema, output_schema to skill_records
ALTER TABLE skill_records
    ADD COLUMN IF NOT EXISTS version       VARCHAR(64)  NOT NULL DEFAULT '1.0.0',
    ADD COLUMN IF NOT EXISTS input_schema  JSONB        NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS output_schema JSONB        NOT NULL DEFAULT '{}';
