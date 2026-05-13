"""GET /trends/{brand} — on-demand trend analysis for a brand."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from agents.trend_analyzer import TrendAnalyzerAgent, TrendReport
from db import queries
from db.connection import get_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trends", tags=["trends"])

_trend_agent = TrendAnalyzerAgent()


class TrendResponse(BaseModel):
    brand: str
    platform: str
    period: str
    report: dict


class TopicEntry(BaseModel):
    topic: str
    mention_count: int


class TopTopicsResponse(BaseModel):
    brand: str
    topics: list[TopicEntry]


@router.get("/{brand}", response_model=TrendResponse)
async def get_brand_trends(
    brand: str,
    platform: str = Query(default="twitter"),
    period: str = Query(default="last 7 days"),
    limit: int = Query(default=30, ge=5, le=100),
) -> TrendResponse:
    """
    Run trend analysis for a brand across its recent signals.
    Results are cached in memory by input hash.
    """
    raw_signals = await queries.get_signals_by_brand(brand, limit=limit)
    if not raw_signals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No signals found for brand '{brand}'",
        )

    # Convert asyncpg records to plain dicts
    signals = []
    for s in raw_signals:
        d = dict(s)
        d["id"] = str(d["id"])
        if d.get("ingested_at"):
            d["ingested_at"] = d["ingested_at"].isoformat()
        signals.append(d)

    try:
        report: TrendReport = await _trend_agent.run_trend_analysis(
            brand=brand,
            platform=platform,
            signals=signals,
            period=period,
        )
        return TrendResponse(
            brand=brand,
            platform=platform,
            period=period,
            report=report.model_dump(),
        )
    except Exception as exc:
        logger.exception("Trend analysis failed for brand=%s", brand)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/{brand}/topics", response_model=TopTopicsResponse)
async def get_top_topics(
    brand: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> TopTopicsResponse:
    """Return top topics for a brand from the materialized view (last 30 days)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT topic, mention_count
            FROM mv_top_topics
            WHERE brand = $1
            ORDER BY mention_count DESC
            LIMIT $2
            """,
            brand, limit,
        )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No topic data found for brand '{brand}'. Run the pipeline first.",
        )
    return TopTopicsResponse(
        brand=brand,
        topics=[TopicEntry(topic=r["topic"], mention_count=r["mention_count"]) for r in rows],
    )
