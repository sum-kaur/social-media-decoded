-- Convenience view: latest insight per brand/platform with action count
CREATE OR REPLACE VIEW latest_insights AS
SELECT DISTINCT ON (brand, platform)
    id,
    brand,
    platform,
    jsonb_array_length(COALESCE(topic_clusters, '[]'::jsonb)) AS cluster_count,
    jsonb_array_length(COALESCE(recommended_actions, '[]'::jsonb)) AS action_count,
    jsonb_array_length(COALESCE(extracted_signals, '[]'::jsonb)) AS signal_count,
    created_at
FROM insights
ORDER BY brand, platform, created_at DESC;

-- View: agent performance summary from pipeline traces
CREATE OR REPLACE VIEW agent_performance AS
SELECT
    trace->>'agent_name' AS agent_name,
    COUNT(*) AS total_calls,
    AVG((trace->>'latency_ms')::FLOAT) AS avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY (trace->>'latency_ms')::FLOAT
    ) AS p95_latency_ms,
    AVG((trace->>'token_count')::INTEGER) AS avg_tokens,
    SUM(CASE WHEN trace->>'error' IS NOT NULL THEN 1 ELSE 0 END) AS error_count
FROM insights,
     jsonb_array_elements(COALESCE(pipeline_trace, '[]'::jsonb)) AS trace
WHERE trace->>'agent_name' IS NOT NULL
GROUP BY trace->>'agent_name';
