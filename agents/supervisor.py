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


def _next_agent(
    completed: set,
    failed: list,
    retry_counts: dict,
) -> str:
    """Pure routing logic — returns the next agent name or 'done'."""
    for agent in _AGENT_ORDER:
        if agent in completed:
            continue
        retries = retry_counts.get(agent, 0)
        if failed.count(agent) > 0 and retries >= _MAX_RETRIES_PER_AGENT:
            logger.error("Agent %s exceeded max retries, skipping", agent)
            continue
        return agent
    return "done"


def supervisor_node(state: PipelineState) -> dict:
    """
    Stateless routing node: inspects PipelineState and sets current_agent.
    Called by LangGraph between each worker node.
    """
    next_agent = _next_agent(
        completed=set(state.get("completed_agents", [])),
        failed=state.get("failed_agents", []),
        retry_counts=state.get("retry_counts", {}),
    )
    logger.info("Supervisor → %s", next_agent)
    return {"current_agent": next_agent}


def route_next(state: PipelineState) -> str:
    """LangGraph edge condition: returns the next node key."""
    current = state.get("current_agent", "")
    if current == "done" or current == "":
        return "done"
    return current
