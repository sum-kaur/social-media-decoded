"""LangGraph graph definition — wires supervisor and worker agents."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.graph import END, StateGraph

from agents.action_recommender import ActionRecommenderAgent
from agents.insight_generator import InsightGeneratorAgent
from agents.signal_extractor import SignalExtractorAgent
from agents.supervisor import route_next, supervisor_node
from agents.topic_clusterer import TopicClustererAgent
from db import queries
from pipeline.state import PipelineState

logger = logging.getLogger(__name__)

# Singleton agent instances — reuse connections across requests
_signal_extractor = SignalExtractorAgent()
_topic_clusterer = TopicClustererAgent()
_insight_generator = InsightGeneratorAgent()
_action_recommender = ActionRecommenderAgent()


async def _run_signal_extractor(state: PipelineState) -> dict:
    return await _signal_extractor.run(state)


async def _run_topic_clusterer(state: PipelineState) -> dict:
    return await _topic_clusterer.run(state)


async def _run_insight_generator(state: PipelineState) -> dict:
    return await _insight_generator.run(state)


async def _run_action_recommender(state: PipelineState) -> dict:
    return await _action_recommender.run(state)


async def _persist_results(state: PipelineState) -> dict:
    """Terminal node: persists pipeline results to DB."""
    try:
        signal_ids = [uuid.UUID(sid) for sid in state.get("signal_ids", [])]
        insight_id = await queries.insert_insight(
            brand=state["brand"],
            platform=state["platform"],
            signal_ids=signal_ids,
            extracted_signals=state.get("extracted_signals", []),
            topic_clusters=state.get("topic_clusters", []),
            insight_text=state.get("insight_text", ""),
            recommended_actions=state.get("recommended_actions", []),
            pipeline_trace=state.get("pipeline_trace", []),
        )
        logger.info("Persisted insight %s for brand=%s", insight_id, state["brand"])
        return {"insight_id": str(insight_id)}
    except Exception as exc:
        logger.exception("Failed to persist pipeline results: %s", exc)
        return {"error": str(exc)}


def build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)

    # Worker nodes
    graph.add_node("signal_extractor", _run_signal_extractor)
    graph.add_node("topic_clusterer", _run_topic_clusterer)
    graph.add_node("insight_generator", _run_insight_generator)
    graph.add_node("action_recommender", _run_action_recommender)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("persist", _persist_results)

    # Entry point through supervisor
    graph.set_entry_point("supervisor")

    # Supervisor routes to appropriate worker
    graph.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "signal_extractor": "signal_extractor",
            "topic_clusterer": "topic_clusterer",
            "insight_generator": "insight_generator",
            "action_recommender": "action_recommender",
            "done": "persist",
        },
    )

    # Each worker feeds back to supervisor
    for agent in ["signal_extractor", "topic_clusterer", "insight_generator", "action_recommender"]:
        graph.add_edge(agent, "supervisor")

    graph.add_edge("persist", END)

    return graph


# Compiled graph singleton
_compiled_graph: Any = None


def get_graph() -> Any:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph


async def run_pipeline(
    brand: str,
    platform: str,
    signal_ids: list[str],
    raw_signals: list[dict],
) -> PipelineState:
    graph = get_graph()

    initial_state: PipelineState = {
        "run_id": str(uuid.uuid4()),
        "brand": brand,
        "platform": platform,
        "signal_ids": signal_ids,
        "raw_signals": raw_signals,
        "extracted_signals": [],
        "topic_clusters": [],
        "marketing_insights": [],
        "recommended_actions": [],
        "current_agent": "",
        "completed_agents": [],
        "failed_agents": [],
        "retry_counts": {},
        "pipeline_trace": [],
        "insight_id": None,
        "error": None,
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state
