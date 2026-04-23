-- Migration: split skill_records.id into UUID pk + slug (human-readable)
-- Run after: add_body_fields.sql
--
-- Before: id = human-readable skill slug, PK
-- After:  id = UUID PK, slug = unique human-readable identifier
--
-- Also renames skill_lineage.child_id/parent_id → child_slug/parent_slug
-- and drops FK constraints that the ORM no longer declares.

-- -------------------------------------------------------------------------
-- 1. Add slug column (copy existing human-readable id into it)
-- -------------------------------------------------------------------------
ALTER TABLE skill_records ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
UPDATE skill_records SET slug = id WHERE slug IS NULL;
ALTER TABLE skill_records ALTER COLUMN slug SET NOT NULL;

-- -------------------------------------------------------------------------
-- 2. Drop all FK constraints pointing at skill_records(id)
--    (names come from PostgreSQL auto-naming; adjust if yours differ)
-- -------------------------------------------------------------------------
ALTER TABLE skill_lineage     DROP CONSTRAINT IF EXISTS skill_lineage_child_id_fkey;
ALTER TABLE skill_lineage     DROP CONSTRAINT IF EXISTS skill_lineage_parent_id_fkey;
ALTER TABLE skill_evolutions  DROP CONSTRAINT IF EXISTS skill_evolutions_parent_skill_id_fkey;
ALTER TABLE skill_evolutions  DROP CONSTRAINT IF EXISTS skill_evolutions_result_record_id_fkey;
ALTER TABLE execution_runs    DROP CONSTRAINT IF EXISTS execution_runs_skill_id_fkey;

-- -------------------------------------------------------------------------
-- 3. Swap skill_records.id from human-readable → UUID
-- -------------------------------------------------------------------------
ALTER TABLE skill_records ADD COLUMN new_id VARCHAR(36);
UPDATE skill_records SET new_id = gen_random_uuid()::text;
ALTER TABLE skill_records ALTER COLUMN new_id SET NOT NULL;

ALTER TABLE skill_records DROP CONSTRAINT skill_records_pkey;
ALTER TABLE skill_records DROP COLUMN id;
ALTER TABLE skill_records RENAME COLUMN new_id TO id;
ALTER TABLE skill_records ADD PRIMARY KEY (id);

-- Unique index on slug
CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_records_slug ON skill_records (slug);

-- -------------------------------------------------------------------------
-- 4. Rename skill_lineage columns
-- -------------------------------------------------------------------------
ALTER TABLE skill_lineage RENAME COLUMN child_id  TO child_slug;
ALTER TABLE skill_lineage RENAME COLUMN parent_id TO parent_slug;

-- Drop old composite PK and re-add with new column names
ALTER TABLE skill_lineage DROP CONSTRAINT IF EXISTS skill_lineage_pkey;
ALTER TABLE skill_lineage ADD PRIMARY KEY (child_slug, parent_slug);

-- Unique constraint expected by the ORM
ALTER TABLE skill_lineage DROP CONSTRAINT IF EXISTS uq_lineage_child_parent;
ALTER TABLE skill_lineage ADD CONSTRAINT uq_lineage_child_parent
    UNIQUE (child_slug, parent_slug);

-- Restore FK constraints using slug
ALTER TABLE skill_lineage ADD CONSTRAINT skill_lineage_child_slug_fkey
    FOREIGN KEY (child_slug) REFERENCES skill_records(slug) ON DELETE CASCADE;
ALTER TABLE skill_lineage ADD CONSTRAINT skill_lineage_parent_slug_fkey
    FOREIGN KEY (parent_slug) REFERENCES skill_records(slug) ON DELETE CASCADE;

-- -------------------------------------------------------------------------
-- 5. skill_evolutions: parent_skill_id and result_record_id now store slugs,
--    no FK (ORM stores them as plain strings for resilience)
-- -------------------------------------------------------------------------
-- (FK was already dropped in step 2; no further action needed)

-- -------------------------------------------------------------------------
-- 6. Refresh FTS index (references same columns, just rebuild to be safe)
-- -------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_skill_records_fts;
CREATE INDEX IF NOT EXISTS idx_skill_records_fts
    ON skill_records USING GIN(
        to_tsvector('english', name || ' ' || description || ' ' || body)
    );
