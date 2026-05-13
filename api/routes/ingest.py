"""POST /ingest — accept raw social signals into the database."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from api.models import (
    BulkIngestRequest,
    BulkIngestResponse,
    SignalIngestRequest,
    SignalIngestResponse,
)
from db import queries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "",
    response_model=SignalIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_signal(body: SignalIngestRequest) -> SignalIngestResponse:
    """Ingest a single social media signal."""
    try:
        signal_id = await queries.insert_signal(
            platform=body.platform,
            brand=body.brand,
            category=body.category,
            post_text=body.post_text,
            campaign_type=body.campaign_type,
            engagements=body.engagements,
            signal_strength=body.signal_strength,
        )
        return SignalIngestResponse(
            signal_id=signal_id,
            ingested_at=datetime.now(tz=timezone.utc),
        )
    except Exception as exc:
        logger.exception("Failed to ingest signal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/bulk",
    response_model=BulkIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_ingest_signals(body: BulkIngestRequest) -> BulkIngestResponse:
    """Ingest multiple signals in a single request (max 500)."""
    signal_ids = []
    for s in body.signals:
        try:
            sid = await queries.insert_signal(
                platform=s.platform,
                brand=s.brand,
                category=s.category,
                post_text=s.post_text,
                campaign_type=s.campaign_type,
                engagements=s.engagements,
                signal_strength=s.signal_strength,
            )
            signal_ids.append(sid)
        except Exception as exc:
            logger.warning("Failed to ingest one signal in bulk: %s", exc)

    return BulkIngestResponse(signal_ids=signal_ids, count=len(signal_ids))
