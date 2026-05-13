-- Tag system: allow flexible labelling of signals without schema changes
CREATE TABLE IF NOT EXISTS signal_tags (
    signal_id UUID REFERENCES signals(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (signal_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_signal_tags_tag ON signal_tags(tag);

-- Denormalised tag array on signals for fast array-contains queries
ALTER TABLE signals ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_signals_tags_gin ON signals USING gin(tags);
