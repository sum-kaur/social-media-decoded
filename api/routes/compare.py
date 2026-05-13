"""POST /compare — compare two brands side by side."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from agents.competitor_analyzer import CompetitorAnalyzerAgent
from db import queries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compare", tags=["analysis"])

_competitor_agent = CompetitorAnalyzerAgent()


class CompareRequest(BaseModel):
    brand_a: str
    brand_b: str
    platform: str = "twitter"
    signal_limit: int = 20


class CompareResponse(BaseModel):
    brand_a: str
    brand_b: str
    platform: str
    report: dict


@router.post("", response_model=CompareResponse)
async def compare_brands(body: CompareRequest) -> CompareResponse:
    """Run competitive analysis between two brands using their recent signals."""
    signals_a, signals_b = await _fetch_and_prep(body.brand_a, body.signal_limit), None

    # Fetch concurrently via asyncio.gather for efficiency
    import asyncio
    signals_a, signals_b = await asyncio.gather(
        _fetch_and_prep(body.brand_a, body.signal_limit),
        _fetch_and_prep(body.brand_b, body.signal_limit),
    )

    if not signals_a:
        raise HTTPException(status_code=404, detail=f"No signals for brand '{body.brand_a}'")
    if not signals_b:
        raise HTTPException(status_code=404, detail=f"No signals for brand '{body.brand_b}'")

    try:
        report = await _competitor_agent.compare(
            brand_a=body.brand_a,
            brand_b=body.brand_b,
            platform=body.platform,
            signals_a=signals_a,
            signals_b=signals_b,
        )
        return CompareResponse(
            brand_a=body.brand_a,
            brand_b=body.brand_b,
            platform=body.platform,
            report=report.model_dump(),
        )
    except Exception as exc:
        logger.exception("Competitor analysis failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _fetch_and_prep(brand: str, limit: int) -> list[dict]:
    raw = await queries.get_signals_by_brand(brand, limit=limit)
    result = []
    for s in raw:
        d = dict(s)
        d["id"] = str(d["id"])
        if d.get("ingested_at"):
            d["ingested_at"] = d["ingested_at"].isoformat()
        result.append(d)
    return result
