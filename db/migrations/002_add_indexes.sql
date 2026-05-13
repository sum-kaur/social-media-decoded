-- Performance indexes added after initial load testing

-- Composite index for the most common query pattern: brand + platform filtered insights
CREATE INDEX IF NOT EXISTS idx_insights_brand_platform
    ON insights(brand, platform, created_at DESC);

-- Partial index for signals with high engagement (hot path for pipeline input selection)
CREATE INDEX IF NOT EXISTS idx_signals_high_engagement
    ON signals(brand, ingested_at DESC)
    WHERE engagements > 1000;

-- GIN index on extracted_signals JSONB for ad-hoc filtering
CREATE INDEX IF NOT EXISTS idx_insights_extracted_signals_gin
    ON insights USING gin(extracted_signals);
