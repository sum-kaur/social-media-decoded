"""GET /signals — paginated signal listing with filtering."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel

from db.connection import acquire

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/signals", tags=["signals"])


class SignalRecord(BaseModel):
    id: uuid.UUID
    platform: str
    brand: str
    category: str
    post_text: str
    campaign_type: str | None
    engagements: int | None
    signal_strength: float | None
    ingested_at: datetime


class SignalListResponse(BaseModel):
    signals: list[SignalRecord]
    total: int
    has_more: bool


@router.get("", response_model=SignalListResponse)
async def list_signals(
    brand: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SignalListResponse:
    """List signals with optional brand/platform filters and pagination."""
    async with acquire() as conn:
        base_where = "WHERE 1=1"
        params: list = []
        idx = 1

        if brand:
            base_where += f" AND brand = ${idx}"
            params.append(brand)
            idx += 1
        if platform:
            base_where += f" AND platform = ${idx}"
            params.append(platform)
            idx += 1

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM signals {base_where}", *params
        )

        rows = await conn.fetch(
            f"""
            SELECT id, platform, brand, category, post_text, campaign_type,
                   engagements, signal_strength, ingested_at
            FROM signals {base_where}
            ORDER BY ingested_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params, limit, offset,
        )

    signals = [SignalRecord(**dict(r)) for r in rows]
    return SignalListResponse(
        signals=signals,
        total=total,
        has_more=(offset + limit) < total,
    )
