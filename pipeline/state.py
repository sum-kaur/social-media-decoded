"""LangGraph pipeline state definition."""
from __future__ import annotations

import uuid
from typing import Any, TypedDict


class AgentTrace(TypedDict):
    agent_name: str
    input_hash: str
    output: Any
    latency_ms: float
    token_count: int
    error: str | None


class PipelineState(TypedDict):
    # Input
    run_id: str
    brand: str
    platform: str
    signal_ids: list[str]
    raw_signals: list[dict]

    # Agent outputs (filled in order)
    extracted_signals: list[dict]    # from signal_extractor
    topic_clusters: list[dict]       # from topic_clusterer
    marketing_insights: list[dict]   # from insight_generator
    recommended_actions: list[dict]  # from action_recommender

    # Intermediate text for DB storage
    insight_text: str

    # Control flow
    current_agent: str
    completed_agents: list[str]
    failed_agents: list[str]
    retry_counts: dict[str, int]

    # Tracing
    pipeline_trace: list[AgentTrace]
    insight_id: str | None
    error: str | None


def empty_state(brand: str, platform: str) -> PipelineState:
    """Return a zeroed-out PipelineState for a new run."""
    return {
        "run_id": str(uuid.uuid4()),
        "brand": brand,
        "platform": platform,
        "signal_ids": [],
        "raw_signals": [],
        "extracted_signals": [],
        "topic_clusters": [],
        "marketing_insights": [],
        "recommended_actions": [],
        "insight_text": "",
        "current_agent": "",
        "completed_agents": [],
        "failed_agents": [],
        "retry_counts": {},
        "pipeline_trace": [],
        "insight_id": None,
        "error": None,
    }
