"""
Utility agent — Trend Analyzer: identifies rising vs declining signals over time.

Not part of the main pipeline; called on-demand for trend reports.
"""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field

from agents.base import BaseAgent


class TrendSignal(BaseModel):
    brand: str
    platform: str
    topic: str
    direction: Literal["rising", "declining", "stable"]
    momentum_score: float = Field(ge=-1, le=1)
    evidence: list[str]


class TrendReport(BaseModel):
    brand: str
    rising_topics: list[TrendSignal]
    declining_topics: list[TrendSignal]
    stable_topics: list[TrendSignal]
    overall_momentum: float = Field(ge=-1, le=1)
    analysis_period: str


_SYSTEM = (
    "You are a social media trend analyst. Given a time-ordered sequence of marketing signals, "
    "identify which topics are rising in engagement, which are declining, and which are stable. "
    "Momentum scores: +1 = strongly rising, 0 = stable, -1 = strongly declining."
)

_TOOL = {
    "name": "analyze_trends",
    "description": "Identify rising, declining, and stable topic trends from signal history.",
    "input_schema": TrendReport.model_json_schema(),
}


class TrendAnalyzerAgent(BaseAgent):
    name = "trend_analyzer"

    async def run_trend_analysis(
        self,
        brand: str,
        platform: str,
        signals: list[dict],
        period: str = "last 7 days",
    ) -> TrendReport:
        input_hash = self._hash({"brand": brand, "platform": platform, "signals": signals})
        start = time.monotonic()

        cached = self._get_cached(f"trends:{input_hash}")
        if cached:
            return TrendReport.model_validate(cached)

        signals_text = "\n".join(
            f"[{s.get('ingested_at', 'unknown')}] {s['platform']} | "
            f"topics: {s.get('topics', [])} | sentiment: {s.get('sentiment', 'unknown')} | "
            f"engagements: {s.get('engagements', 0)}"
            for s in signals
        )

        message = await self._call_llm(
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Brand: {brand} | Platform: {platform} | Period: {period}\n\n"
                    f"Signal history (chronological):\n{signals_text}\n\n"
                    "Identify trend direction for each topic cluster."
                ),
            }],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "analyze_trends"},
        )

        raw = self._extract_tool_input(message)
        report = TrendReport.model_validate(raw)
        self._set_cached(f"trends:{input_hash}", report.model_dump())
        return report
