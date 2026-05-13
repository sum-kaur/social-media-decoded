"""GET /analytics — aggregated pipeline and agent performance stats."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from db.connection import get_pool
from pipeline.metrics import get_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _query_agent_performance() -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                agent_name,
                COUNT(*) AS total_calls,
                COUNT(*) FILTER (WHERE error IS NOT NULL) AS error_calls,
                ROUND(AVG(latency_ms)::numeric, 1) AS avg_latency_ms,
                ROUND(
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 1
                ) AS p95_latency_ms
            FROM insights,
                 LATERAL jsonb_to_recordset(pipeline_trace::jsonb)
                   AS t(agent_name text, latency_ms float, error text)
            GROUP BY agent_name
            ORDER BY total_calls DESC
            """
        )
    return [dict(r) for r in rows]


async def _query_brand_summary() -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                brand,
                COUNT(DISTINCT id) AS insight_count,
                MAX(created_at) AS latest_insight_at
            FROM insights
            GROUP BY brand
            ORDER BY insight_count DESC
            """
        )
    return [dict(r) for r in rows]


async def _query_pipeline_run_summary() -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS total_runs,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed_runs,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
                ROUND(AVG(duration_ms)::numeric, 1) AS avg_duration_ms
            FROM pipeline_runs
            """
        )
    return dict(row) if row else {}


@router.get("")
async def get_analytics() -> dict:
    """Return aggregated analytics: agent performance, brand summaries, run stats."""
    agent_db, brands, run_summary = (
        await _query_agent_performance(),
        await _query_brand_summary(),
        await _query_pipeline_run_summary(),
    )

    # Merge live in-process metrics with DB-persisted trace data
    live_metrics = get_registry().snapshot()

    return {
        "agent_performance_db": agent_db,
        "agent_performance_live": live_metrics,
        "brand_summary": brands,
        "pipeline_run_summary": run_summary,
    }
