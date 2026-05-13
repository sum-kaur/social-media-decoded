"""Agent 4 — Action Recommender: turns insights into prioritised next actions."""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel

from agents.base import BaseAgent
from pipeline.state import PipelineState


class ActionRecommendation(BaseModel):
    action: str
    rationale: str
    priority: Literal["high", "medium", "low"]
    platform: str
    timeframe: str


class ActionResult(BaseModel):
    recommendations: list[ActionRecommendation]


_SYSTEM = (
    "You are a digital marketing campaign manager. "
    "Given marketing insights derived from social media signals, "
    "recommend concrete, prioritised actions a marketing team should take. "
    "Be specific: name the channel, timing, and expected outcome."
)

_TOOL = {
    "name": "recommend_actions",
    "description": "Generate prioritised marketing action recommendations.",
    "input_schema": ActionResult.model_json_schema(),
}


class ActionRecommenderAgent(BaseAgent):
    name = "action_recommender"

    async def run(self, state: PipelineState) -> dict:
        insights = state["marketing_insights"]
        brand = state["brand"]
        platform = state["platform"]
        input_hash = self._hash({"insights": insights, "brand": brand, "platform": platform})

        start = time.monotonic()

        cached = self._get_cached(f"actions:{input_hash}")
        if cached:
            latency = (time.monotonic() - start) * 1000
            trace = self._build_trace_entry(input_hash, cached, latency, 0)
            return {
                "recommended_actions": cached,
                "pipeline_trace": state.get("pipeline_trace", []) + [trace],
                "completed_agents": state.get("completed_agents", []) + [self.name],
                "current_agent": "done",
            }

        insights_text = "\n\n".join(
            f"Insight (confidence {i['confidence']:.0%}): {i['summary']}\n"
            f"What it means: {i['what_it_means']}\n"
            f"Supporting signals: {', '.join(i['supporting_signals'][:3])}"
            for i in insights
        )

        message = await self._call_llm(
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Brand: {brand} | Primary Platform: {platform}\n\n"
                    f"Marketing Insights:\n{insights_text}\n\n"
                    "Recommend the top actions this brand should take in the next 30 days. "
                    "Prioritise by impact. Include specific timeframes."
                ),
            }],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "recommend_actions"},
        )

        raw_output = self._extract_tool_input(message)
        result = ActionResult.model_validate(raw_output)
        serialized = [r.model_dump() for r in result.recommendations]

        self._set_cached(f"actions:{input_hash}", serialized)

        latency = (time.monotonic() - start) * 1000
        token_count = message.usage.input_tokens + message.usage.output_tokens
        trace = self._build_trace_entry(input_hash, serialized, latency, token_count)

        return {
            "recommended_actions": serialized,
            "pipeline_trace": state.get("pipeline_trace", []) + [trace],
            "completed_agents": state.get("completed_agents", []) + [self.name],
            "current_agent": "done",
        }
