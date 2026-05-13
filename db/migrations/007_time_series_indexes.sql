-- Migration 007: add time-series indexes for trend queries and analytics aggregations

-- Partial index: recent signals (last 90 days) used by trend and analytics queries
CREATE INDEX IF NOT EXISTS idx_signals_recent
    ON signals (brand, platform, created_at DESC)
    WHERE created_at > NOW() - INTERVAL '90 days';

-- Brin index on created_at — efficient range scans over large append-only signal table
-- BRIN is much smaller than btree for naturally-ordered time-series data
CREATE INDEX IF NOT EXISTS idx_signals_created_at_brin
    ON signals USING BRIN (created_at)
    WITH (pages_per_range = 128);

-- Covering index for the /signals paginated endpoint to avoid heap fetches
CREATE INDEX IF NOT EXISTS idx_signals_brand_platform_covering
    ON signals (brand, platform, created_at DESC)
    INCLUDE (id, sentiment, signal_strength, engagements);

-- Pipeline runs: speed up brand-filtered history queries
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_brand_started
    ON pipeline_runs (brand, started_at DESC);

-- Insights: speed up latest-per-brand lookup used by the latest_insights view
CREATE INDEX IF NOT EXISTS idx_insights_brand_platform_created
    ON insights (brand, platform, created_at DESC);
