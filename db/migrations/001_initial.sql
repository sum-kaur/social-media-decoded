-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Signals table: raw social media post data
CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    brand TEXT NOT NULL,
    category TEXT NOT NULL,
    post_text TEXT NOT NULL,
    campaign_type TEXT,
    engagements INTEGER,
    signal_strength FLOAT,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_brand ON signals(brand);
CREATE INDEX IF NOT EXISTS idx_signals_platform ON signals(platform);
CREATE INDEX IF NOT EXISTS idx_signals_ingested_at ON signals(ingested_at DESC);

-- Embeddings table: pgvector for semantic similarity search
CREATE TABLE IF NOT EXISTS signal_embeddings (
    signal_id UUID REFERENCES signals(id) ON DELETE CASCADE,
    embedding vector(1536),
    model TEXT DEFAULT 'voyage-3',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (signal_id)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON signal_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Insights table: pipeline outputs per brand/platform run
CREATE TABLE IF NOT EXISTS insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand TEXT NOT NULL,
    platform TEXT NOT NULL,
    signal_ids UUID[],
    extracted_signals JSONB,
    topic_clusters JSONB,
    insight_text TEXT,
    recommended_actions JSONB,
    pipeline_trace JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insights_brand ON insights(brand);
CREATE INDEX IF NOT EXISTS idx_insights_created_at ON insights(created_at DESC);
