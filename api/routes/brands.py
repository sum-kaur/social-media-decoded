"""GET /brands — list brands and their signal counts."""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from db.connection import acquire

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brands", tags=["brands"])


class BrandSummary(BaseModel):
    brand: str
    signal_count: int
    platforms: list[str]
    latest_ingested_at: str | None


class BrandListResponse(BaseModel):
    brands: list[BrandSummary]
    total: int


@router.get("", response_model=BrandListResponse)
async def list_brands() -> BrandListResponse:
    """Return all brands with their signal counts and active platforms."""
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                brand,
                COUNT(*) AS signal_count,
                ARRAY_AGG(DISTINCT platform) AS platforms,
                MAX(ingested_at)::TEXT AS latest_ingested_at
            FROM signals
            GROUP BY brand
            ORDER BY signal_count DESC
            """
        )

    brands = [
        BrandSummary(
            brand=r["brand"],
            signal_count=r["signal_count"],
            platforms=list(r["platforms"]),
            latest_ingested_at=r["latest_ingested_at"],
        )
        for r in rows
    ]
    return BrandListResponse(brands=brands, total=len(brands))
