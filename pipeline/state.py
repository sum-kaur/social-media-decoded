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

    # Control flow
    current_agent: str
    completed_agents: list[str]
    failed_agents: list[str]
    retry_counts: dict[str, int]

    # Tracing
    pipeline_trace: list[AgentTrace]
    insight_id: str | None
    error: str | None
