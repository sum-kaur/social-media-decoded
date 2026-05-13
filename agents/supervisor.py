"""Supervisor agent — decides which worker to dispatch next based on pipeline state."""
from __future__ import annotations

import logging

from pipeline.state import PipelineState

logger = logging.getLogger(__name__)

_AGENT_ORDER = [
    "signal_extractor",
    "topic_clusterer",
    "insight_generator",
    "action_recommender",
]

_MAX_RETRIES_PER_AGENT = 2


def supervisor_node(state: PipelineState) -> dict:
    """
    Stateless routing function: inspects PipelineState and returns the next node name.
    Called by LangGraph as a conditional edge resolver.
    """
    completed = set(state.get("completed_agents", []))
    failed = state.get("failed_agents", [])
    retry_counts = state.get("retry_counts", {})

    for agent in _AGENT_ORDER:
        if agent in completed:
            continue

        retries = retry_counts.get(agent, 0)
        if failed.count(agent) > 0 and retries >= _MAX_RETRIES_PER_AGENT:
            logger.error("Agent %s exceeded max retries (%d), skipping", agent, _MAX_RETRIES_PER_AGENT)
            # Skip to next agent
            continue

        logger.info("Supervisor routing to: %s (retry #%d)", agent, retries)
        return {"current_agent": agent}

    return {"current_agent": "done"}


def route_next(state: PipelineState) -> str:
    """LangGraph edge condition: returns the next node key."""
    current = state.get("current_agent", "")
    if current == "done" or current == "":
        return "done"
    return current
