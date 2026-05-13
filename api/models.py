"""Pydantic v2 request and response models for the API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class SignalIngestRequest(BaseModel):
    platform: str = Field(..., examples=["twitter", "instagram", "tiktok"])
    brand: str = Field(..., examples=["Nike"])
    category: str = Field(..., examples=["sportswear"])
    post_text: str = Field(..., min_length=1, max_length=5000)
    campaign_type: str | None = Field(default=None, examples=["product_launch"])
    engagements: int | None = Field(default=None, ge=0)
    signal_strength: float | None = Field(default=None, ge=0, le=1)
    source_url: str | None = Field(default=None)
    author_handle: str | None = Field(default=None)
    language: str = Field(default="en", max_length=10)
    is_verified_author: bool = Field(default=False)


class SignalIngestResponse(BaseModel):
    signal_id: uuid.UUID
    ingested_at: datetime


class BulkIngestRequest(BaseModel):
    signals: list[SignalIngestRequest] = Field(..., min_length=1, max_length=500)


class BulkIngestResponse(BaseModel):
    signal_ids: list[uuid.UUID]
    count: int


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class PipelineRunRequest(BaseModel):
    brand: str
    platform: str
    signal_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Specific signal IDs to process. If omitted, fetches latest 50 for brand.",
    )


class PipelineRunResponse(BaseModel):
    run_id: str
    insight_id: uuid.UUID | None
    brand: str
    platform: str
    agents_completed: list[str]
    error: str | None = None


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

class InsightResponse(BaseModel):
    id: uuid.UUID
    brand: str
    platform: str
    signal_ids: list[uuid.UUID]
    extracted_signals: list[dict]
    topic_clusters: list[dict]
    insight_text: str | None
    recommended_actions: list[dict]
    pipeline_trace: list[dict]
    created_at: datetime


class InsightListResponse(BaseModel):
    insights: list[InsightResponse]
    total: int


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: bool
    version: str = "1.0.0"
