"""GET /runs — pipeline run history and status."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel

from db import queries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runs", tags=["runs"])


class PipelineRunRecord(BaseModel):
    run_id: str
    brand: str
    platform: str
    status: str
    agents_completed: list[str] | None
    agents_failed: list[str] | None
    signal_count: int | None
    duration_ms: float | None
    error: str | None
    started_at: str
    completed_at: str | None


class RunListResponse(BaseModel):
    runs: list[PipelineRunRecord]
    total: int


@router.get("", response_model=RunListResponse)
async def list_runs(
    brand: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> RunListResponse:
    """List pipeline run history, newest first."""
    rows = await queries.get_pipeline_runs(brand=brand, limit=limit)
    runs = [
        PipelineRunRecord(
            run_id=r["run_id"],
            brand=r["brand"],
            platform=r["platform"],
            status=r["status"],
            agents_completed=r.get("agents_completed"),
            agents_failed=r.get("agents_failed"),
            signal_count=r.get("signal_count"),
            duration_ms=r.get("duration_ms"),
            error=r.get("error"),
            started_at=r["started_at"].isoformat(),
            completed_at=r["completed_at"].isoformat() if r.get("completed_at") else None,
        )
        for r in rows
    ]
    return RunListResponse(runs=runs, total=len(runs))
