"""Agent 2 — Topic Clusterer: groups signals into semantic topic clusters."""
from __future__ import annotations

import time

from pydantic import BaseModel, Field

from agents.base import BaseAgent
from pipeline.state import PipelineState


class TopicCluster(BaseModel):
    cluster_id: str
    topic_label: str
    signals: list[str]       # list of signal brand+platform keys
    dominant_sentiment: str
    engagement_weight: float = Field(ge=0, le=1)


class ClusteringResult(BaseModel):
    clusters: list[TopicCluster]


_SYSTEM = (
    "You are a topic clustering expert for social media marketing data. "
    "Given extracted marketing signals, group them into coherent topic clusters. "
    "Each cluster should represent a distinct marketing theme or trend."
)

_TOOL = {
    "name": "cluster_topics",
    "description": "Group extracted signals into topic clusters.",
    "input_schema": ClusteringResult.model_json_schema(),
}


class TopicClustererAgent(BaseAgent):
    name = "topic_clusterer"

    async def run(self, state: PipelineState) -> dict:
        extracted = state["extracted_signals"]
        input_hash = self._hash(extracted)

        start = time.monotonic()

        cached = self._get_cached(f"clusterer:{input_hash}")
        if cached:
            latency = (time.monotonic() - start) * 1000
            trace = self._build_trace_entry(input_hash, cached, latency, 0)
            return {
                "topic_clusters": cached,
                "pipeline_trace": state.get("pipeline_trace", []) + [trace],
                "completed_agents": state.get("completed_agents", []) + [self.name],
                "current_agent": "insight_generator",
            }

        signals_text = "\n".join(
            f"- Brand: {s['brand']}, Platform: {s['platform']}, "
            f"Sentiment: {s['sentiment']}, Topics: {s['topics']}, "
            f"Trend Score: {s['trend_score']:.2f}, Phrases: {s['key_phrases']}"
            for s in extracted
        )

        message = await self._call_llm(
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Cluster these extracted signals by topic:\n\n{signals_text}\n\n"
                    "Create meaningful clusters that would help a marketing team prioritize."
                ),
            }],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "cluster_topics"},
        )

        raw_output = self._extract_tool_input(message)
        result = ClusteringResult.model_validate(raw_output)
        serialized = [c.model_dump() for c in result.clusters]

        self._set_cached(f"clusterer:{input_hash}", serialized)

        latency = (time.monotonic() - start) * 1000
        token_count = message.usage.input_tokens + message.usage.output_tokens
        trace = self._build_trace_entry(input_hash, serialized, latency, token_count)

        return {
            "topic_clusters": serialized,
            "pipeline_trace": state.get("pipeline_trace", []) + [trace],
            "completed_agents": state.get("completed_agents", []) + [self.name],
            "current_agent": "insight_generator",
        }
