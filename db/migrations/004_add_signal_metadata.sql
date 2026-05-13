-- Add metadata columns to signals table for richer filtering and deduplication
ALTER TABLE signals
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS author_handle TEXT,
    ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en',
    ADD COLUMN IF NOT EXISTS is_verified_author BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS raw_metadata JSONB;

-- Deduplication: prevent exact same post_text for same brand+platform
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_dedup
    ON signals(brand, platform, md5(post_text));

-- Index for language-filtered queries
CREATE INDEX IF NOT EXISTS idx_signals_language
    ON signals(language, brand);
