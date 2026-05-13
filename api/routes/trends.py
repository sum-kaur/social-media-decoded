"""GET /trends/{brand} — on-demand trend analysis for a brand."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from agents.trend_analyzer import TrendAnalyzerAgent, TrendReport
from db import queries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trends", tags=["trends"])

_trend_agent = TrendAnalyzerAgent()


class TrendResponse(BaseModel):
    brand: str
    platform: str
    period: str
    report: dict


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
