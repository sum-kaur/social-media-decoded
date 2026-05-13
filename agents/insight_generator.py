"""Agent 3 — Insight Generator: translates clusters into marketing insights."""
from __future__ import annotations

import time

from pydantic import BaseModel, Field

from agents.base import BaseAgent
from pipeline.state import PipelineState


class MarketingInsight(BaseModel):
    summary: str
    what_it_means: str
    confidence: float = Field(ge=0, le=1)
    supporting_signals: list[str]


class InsightResult(BaseModel):
    insights: list[MarketingInsight]


_SYSTEM = (
    "You are a senior marketing strategist who interprets social media signal clusters "
    "and translates them into actionable business insights. "
    "Be specific, data-driven, and direct about what each cluster means for brand strategy."
)

_TOOL = {
    "name": "generate_insights",
    "description": "Generate marketing insights from topic clusters.",
    "input_schema": InsightResult.model_json_schema(),
}


class InsightGeneratorAgent(BaseAgent):
    name = "insight_generator"

    async def run(self, state: PipelineState) -> dict:
        clusters = state["topic_clusters"]
        extracted = state["extracted_signals"]
        brand = state["brand"]
        platform = state["platform"]
        input_hash = self._hash({"clusters": clusters, "brand": brand, "platform": platform})

        start = time.monotonic()

        cached = self._get_cached(f"insights:{input_hash}")
        if cached:
            latency = (time.monotonic() - start) * 1000
            trace = self._build_trace_entry(input_hash, cached, latency, 0)
            return {
                "marketing_insights": cached,
                "pipeline_trace": state.get("pipeline_trace", []) + [trace],
                "completed_agents": state.get("completed_agents", []) + [self.name],
                "current_agent": "action_recommender",
            }

        clusters_text = "\n".join(
            f"Cluster '{c['cluster_id']}' — {c['topic_label']}: "
            f"{len(c['signals'])} signals, dominant sentiment: {c['dominant_sentiment']}, "
            f"engagement weight: {c['engagement_weight']:.2f}"
            for c in clusters
        )

        message = await self._call_llm(
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Brand: {brand} | Platform: {platform}\n\n"
                    f"Topic Clusters:\n{clusters_text}\n\n"
                    f"Total signals analysed: {len(extracted)}\n\n"
                    "What does this mean for our marketing strategy? "
                    "Generate specific, actionable insights with confidence scores."
                ),
            }],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "generate_insights"},
        )

        raw_output = self._extract_tool_input(message)
        result = InsightResult.model_validate(raw_output)
        serialized = [i.model_dump() for i in result.insights]

        self._set_cached(f"insights:{input_hash}", serialized)

        latency = (time.monotonic() - start) * 1000
        token_count = message.usage.input_tokens + message.usage.output_tokens
        trace = self._build_trace_entry(input_hash, serialized, latency, token_count)

        # Flatten insight text for DB storage
        insight_text = "\n\n".join(
            f"**{ins['summary']}**\n{ins['what_it_means']}"
            for ins in serialized
        )

        return {
            "marketing_insights": serialized,
            "insight_text": insight_text,
            "pipeline_trace": state.get("pipeline_trace", []) + [trace],
            "completed_agents": state.get("completed_agents", []) + [self.name],
            "current_agent": "action_recommender",
        }
