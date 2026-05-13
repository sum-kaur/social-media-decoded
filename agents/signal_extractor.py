"""Agent 1 — Signal Extractor: classifies and enriches raw social posts."""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field

from agents.base import BaseAgent
from pipeline.state import PipelineState


class ExtractedSignal(BaseModel):
    brand: str
    platform: str
    sentiment: Literal["positive", "negative", "neutral"]
    topics: list[str]
    trend_score: float = Field(ge=0, le=1)
    key_phrases: list[str]


class ExtractionResult(BaseModel):
    signals: list[ExtractedSignal]


_SYSTEM = (
    "You are a social media signal extraction specialist. "
    "Given raw social media posts, extract structured marketing signals. "
    "Focus on brand sentiment, emerging topics, and engagement-weighted trends."
)

_TOOL = {
    "name": "extract_signals",
    "description": "Extract and classify marketing signals from raw social posts.",
    "input_schema": ExtractionResult.model_json_schema(),
}


class SignalExtractorAgent(BaseAgent):
    name = "signal_extractor"

    async def run(self, state: PipelineState) -> dict:
        raw_signals = state["raw_signals"]
        input_hash = self._hash(raw_signals)

        start = time.monotonic()

        cached = self._get_cached(f"extractor:{input_hash}")
        if cached:
            latency = (time.monotonic() - start) * 1000
            trace = self._build_trace_entry(input_hash, cached, latency, 0)
            return {
                "extracted_signals": cached,
                "pipeline_trace": state.get("pipeline_trace", []) + [trace],
                "completed_agents": state.get("completed_agents", []) + [self.name],
                "current_agent": "topic_clusterer",
            }

        posts_text = "\n\n".join(
            f"[{s['platform']}] {s['brand']}: {s['post_text']}"
            for s in raw_signals
        )

        message = await self._call_llm(
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"Extract signals from these posts:\n\n{posts_text}"}],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "extract_signals"},
        )

        raw_output = self._extract_tool_input(message)
        result = ExtractionResult.model_validate(raw_output)
        serialized = [s.model_dump() for s in result.signals]

        self._set_cached(f"extractor:{input_hash}", serialized)

        latency = (time.monotonic() - start) * 1000
        token_count = message.usage.input_tokens + message.usage.output_tokens
        trace = self._build_trace_entry(input_hash, serialized, latency, token_count)

        return {
            "extracted_signals": serialized,
            "pipeline_trace": state.get("pipeline_trace", []) + [trace],
            "completed_agents": state.get("completed_agents", []) + [self.name],
            "current_agent": "topic_clusterer",
        }
