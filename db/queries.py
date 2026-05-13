"""Raw SQL query functions — no ORM, just asyncpg."""
from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg

from db.connection import acquire


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

async def insert_signal(
    platform: str,
    brand: str,
    category: str,
    post_text: str,
    campaign_type: str | None = None,
    engagements: int | None = None,
    signal_strength: float | None = None,
) -> uuid.UUID:
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO signals (platform, brand, category, post_text, campaign_type, engagements, signal_strength)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            platform, brand, category, post_text, campaign_type, engagements, signal_strength,
        )
        return row["id"]


async def get_signals_by_brand(brand: str, limit: int = 100) -> list[dict]:
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, platform, brand, category, post_text, campaign_type,
                   engagements, signal_strength, ingested_at
            FROM signals
            WHERE brand = $1
            ORDER BY ingested_at DESC
            LIMIT $2
            """,
            brand, limit,
        )
        return [dict(r) for r in rows]


async def get_signals_by_ids(signal_ids: list[uuid.UUID]) -> list[dict]:
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM signals WHERE id = ANY($1::uuid[])",
            signal_ids,
        )
        return [dict(r) for r in rows]


async def get_signal_count_by_brand(brand: str) -> int:
    async with acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE brand = $1", brand
        )


async def delete_signals_by_brand(brand: str) -> int:
    """Delete all signals for a brand. Returns count of deleted rows."""
    async with acquire() as conn:
        result = await conn.execute(
            "DELETE FROM signals WHERE brand = $1", brand
        )
        return int(result.split()[-1])


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

async def upsert_embedding(
    signal_id: uuid.UUID,
    embedding: list[float],
    model: str = "voyage-3",
) -> None:
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO signal_embeddings (signal_id, embedding, model)
            VALUES ($1, $2::vector, $3)
            ON CONFLICT (signal_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    model = EXCLUDED.model,
                    created_at = NOW()
            """,
            signal_id, embedding, model,
        )


async def find_similar_signals(
    embedding: list[float],
    limit: int = 10,
    threshold: float = 0.8,
) -> list[dict]:
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.*, 1 - (se.embedding <=> $1::vector) AS similarity
            FROM signal_embeddings se
            JOIN signals s ON s.id = se.signal_id
            WHERE 1 - (se.embedding <=> $1::vector) >= $2
            ORDER BY se.embedding <=> $1::vector
            LIMIT $3
            """,
            embedding, threshold, limit,
        )
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

async def insert_insight(
    brand: str,
    platform: str,
    signal_ids: list[uuid.UUID],
    extracted_signals: Any,
    topic_clusters: Any,
    insight_text: str,
    recommended_actions: Any,
    pipeline_trace: Any,
) -> uuid.UUID:
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO insights
                (brand, platform, signal_ids, extracted_signals, topic_clusters,
                 insight_text, recommended_actions, pipeline_trace)
            VALUES ($1, $2, $3::uuid[], $4::jsonb, $5::jsonb, $6, $7::jsonb, $8::jsonb)
            RETURNING id
            """,
            brand,
            platform,
            signal_ids,
            json.dumps(extracted_signals),
            json.dumps(topic_clusters),
            insight_text,
            json.dumps(recommended_actions),
            json.dumps(pipeline_trace),
        )
        return row["id"]


async def get_insights(brand: str | None = None, limit: int = 20) -> list[dict]:
    async with acquire() as conn:
        if brand:
            rows = await conn.fetch(
                "SELECT * FROM insights WHERE brand = $1 ORDER BY created_at DESC LIMIT $2",
                brand, limit,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM insights ORDER BY created_at DESC LIMIT $1",
                limit,
            )
        return [dict(r) for r in rows]


async def get_insight_by_id(insight_id: uuid.UUID) -> dict | None:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM insights WHERE id = $1",
            insight_id,
        )
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Pipeline runs
# ---------------------------------------------------------------------------

async def insert_pipeline_run(
    run_id: str,
    brand: str,
    platform: str,
    signal_count: int,
) -> None:
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO pipeline_runs (run_id, brand, platform, signal_count, status)
            VALUES ($1, $2, $3, $4, 'running')
            ON CONFLICT (run_id) DO NOTHING
            """,
            run_id, brand, platform, signal_count,
        )


async def complete_pipeline_run(
    run_id: str,
    agents_completed: list[str],
    agents_failed: list[str],
    insight_id: uuid.UUID | None,
    duration_ms: float,
    error: str | None = None,
) -> None:
    status = "failed" if error else "completed"
    async with acquire() as conn:
        await conn.execute(
            """
            UPDATE pipeline_runs
            SET status = $1,
                agents_completed = $2,
                agents_failed = $3,
                insight_id = $4,
                completed_at = NOW(),
                duration_ms = $5,
                error = $6
            WHERE run_id = $7
            """,
            status, agents_completed, agents_failed,
            insight_id, duration_ms, error, run_id,
        )


async def get_pipeline_runs(brand: str | None = None, limit: int = 20) -> list[dict]:
    async with acquire() as conn:
        if brand:
            rows = await conn.fetch(
                "SELECT * FROM pipeline_runs WHERE brand = $1 ORDER BY started_at DESC LIMIT $2",
                brand, limit,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT $1", limit
            )
        return [dict(r) for r in rows]
