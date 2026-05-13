-- Pipeline run audit table: tracks every invocation with timing and agent completion status
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id TEXT NOT NULL UNIQUE,
    brand TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',  -- running | completed | failed
    agents_completed TEXT[],
    agents_failed TEXT[],
    signal_count INTEGER,
    insight_id UUID REFERENCES insights(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms FLOAT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_brand ON pipeline_runs(brand, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
