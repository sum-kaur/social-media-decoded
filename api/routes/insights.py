"""GET /insights — retrieve pipeline results."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from api.models import InsightListResponse, InsightResponse
from db import queries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/insights", tags=["insights"])


def _row_to_response(row: dict) -> InsightResponse:
    return InsightResponse(
        id=row["id"],
        brand=row["brand"],
        platform=row["platform"],
        signal_ids=row.get("signal_ids") or [],
        extracted_signals=row.get("extracted_signals") or [],
        topic_clusters=row.get("topic_clusters") or [],
        insight_text=row.get("insight_text"),
        recommended_actions=row.get("recommended_actions") or [],
        pipeline_trace=row.get("pipeline_trace") or [],
        created_at=row["created_at"],
    )


@router.get("", response_model=InsightListResponse)
async def list_insights(
    brand: str | None = Query(default=None, description="Filter by brand name"),
    limit: int = Query(default=20, ge=1, le=100),
) -> InsightListResponse:
    """List pipeline insights, optionally filtered by brand."""
    rows = await queries.get_insights(brand=brand, limit=limit)
    return InsightListResponse(
        insights=[_row_to_response(r) for r in rows],
        total=len(rows),
    )


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(insight_id: uuid.UUID) -> InsightResponse:
    """Fetch a single insight by ID."""
    row = await queries.get_insight_by_id(insight_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insight {insight_id} not found",
        )
    return _row_to_response(row)
