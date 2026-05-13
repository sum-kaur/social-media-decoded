-- Migration 008: materialized views for analytics queries
-- Refreshed on-demand via REFRESH MATERIALIZED VIEW CONCURRENTLY

-- Materialized view: signal stats per brand/platform/day
-- Used by /analytics and trend queries to avoid full-table aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_signal_daily_stats AS
SELECT
    brand,
    platform,
    DATE_TRUNC('day', created_at) AS day,
    COUNT(*) AS signal_count,
    AVG(signal_strength) AS avg_signal_strength,
    SUM(engagements) AS total_engagements,
    COUNT(*) FILTER (WHERE sentiment = 'positive') AS positive_count,
    COUNT(*) FILTER (WHERE sentiment = 'negative') AS negative_count,
    COUNT(*) FILTER (WHERE sentiment = 'neutral') AS neutral_count
FROM signals
GROUP BY brand, platform, DATE_TRUNC('day', created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_signal_daily_stats
    ON mv_signal_daily_stats (brand, platform, day);

-- Materialized view: top topics per brand (last 30 days)
-- Derived from JSONB extracted_signals in insights table
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_topics AS
SELECT
    brand,
    topic,
    COUNT(*) AS mention_count
FROM insights,
     LATERAL jsonb_array_elements(extracted_signals::jsonb) AS es,
     LATERAL jsonb_array_elements_text(es->'topics') AS topic
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY brand, topic
ORDER BY brand, mention_count DESC;

CREATE INDEX IF NOT EXISTS idx_mv_top_topics_brand
    ON mv_top_topics (brand, mention_count DESC);

-- Function to refresh all materialized views (call from maintenance cron)
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_signal_daily_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_topics;
END;
$$;
