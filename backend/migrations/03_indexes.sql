-- Vector indexes — created after seed data so ivfflat has rows to work with
CREATE INDEX IF NOT EXISTS idx_skill_records_embedding
    ON skill_records USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

CREATE INDEX IF NOT EXISTS idx_category_prototypes_embedding
    ON category_prototypes USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
