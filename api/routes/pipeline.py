"""POST /pipeline/run — trigger the 4-agent analysis pipeline."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, status

from api.models import PipelineRunRequest, PipelineRunResponse
from db import queries
from pipeline.orchestrator import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post(
    "/run",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_200_OK,
)
async def run_pipeline_endpoint(body: PipelineRunRequest) -> PipelineRunResponse:
    """
    Trigger the full 4-agent pipeline for a brand/platform.

    If signal_ids are not provided, fetches the 50 most recent signals
    for the brand from the database.
    """
    try:
        if body.signal_ids:
            raw_signals = await queries.get_signals_by_ids(body.signal_ids)
            signal_id_strs = [str(sid) for sid in body.signal_ids]
        else:
            raw_signals = await queries.get_signals_by_brand(body.brand, limit=50)
            signal_id_strs = [str(s["id"]) for s in raw_signals]

        if not raw_signals:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No signals found for brand '{body.brand}'",
            )

        # Convert asyncpg Records to plain dicts and stringify UUIDs
        signals_dicts = []
        for s in raw_signals:
            d = dict(s)
            d["id"] = str(d["id"])
            signals_dicts.append(d)

        final_state = await run_pipeline(
            brand=body.brand,
            platform=body.platform,
            signal_ids=signal_id_strs,
            raw_signals=signals_dicts,
        )

        insight_id = final_state.get("insight_id")

        return PipelineRunResponse(
            run_id=final_state["run_id"],
            insight_id=uuid.UUID(insight_id) if insight_id else None,
            brand=body.brand,
            platform=body.platform,
            agents_completed=final_state.get("completed_agents", []),
            error=final_state.get("error"),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Pipeline run failed for brand=%s", body.brand)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
