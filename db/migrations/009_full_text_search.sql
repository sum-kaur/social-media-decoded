-- Migration 009: full-text search on signal post_text
-- Adds a tsvector column with a GIN index for fast keyword search

ALTER TABLE signals ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', post_text)) STORED;

CREATE INDEX IF NOT EXISTS idx_signals_search_vector
    ON signals USING GIN (search_vector);

-- Helper function: search signals by keyword(s) with optional brand filter
CREATE OR REPLACE FUNCTION search_signals(
    query_text TEXT,
    p_brand    TEXT DEFAULT NULL,
    p_limit    INT  DEFAULT 20
)
RETURNS TABLE (
    id              UUID,
    brand           TEXT,
    platform        TEXT,
    post_text       TEXT,
    sentiment       TEXT,
    signal_strength FLOAT,
    rank            FLOAT
) LANGUAGE sql STABLE AS $$
    SELECT
        s.id,
        s.brand,
        s.platform,
        s.post_text,
        s.sentiment,
        s.signal_strength,
        ts_rank(s.search_vector, query) AS rank
    FROM signals s,
         to_tsquery('english', query_text) AS query
    WHERE s.search_vector @@ query
      AND (p_brand IS NULL OR s.brand = p_brand)
    ORDER BY rank DESC, s.signal_strength DESC
    LIMIT p_limit;
$$;
