"""
Competitor Analysis Agent — compares signal patterns across brands.

Surfaces relative positioning: where is Brand A winning vs Brand B?
"""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field

from agents.base import BaseAgent


class CompetitorComparison(BaseModel):
    aspect: str
    brand_a_score: float = Field(ge=0, le=1)
    brand_b_score: float = Field(ge=0, le=1)
    winner: Literal["brand_a", "brand_b", "tied"]
    insight: str


class CompetitorReport(BaseModel):
    brand_a: str
    brand_b: str
    platform: str
    comparisons: list[CompetitorComparison]
    overall_winner: Literal["brand_a", "brand_b", "tied"]
    strategic_recommendation: str


_SYSTEM = (
    "You are a competitive intelligence analyst for social media marketing. "
    "Given signal data for two competing brands, compare them across key dimensions: "
    "engagement rate, sentiment, topic diversity, virality, and campaign effectiveness."
)

_TOOL = {
    "name": "compare_competitors",
    "description": "Compare two brands across marketing signal dimensions.",
    "input_schema": CompetitorReport.model_json_schema(),
}


class CompetitorAnalyzerAgent(BaseAgent):
    name = "competitor_analyzer"

    async def compare(
        self,
        brand_a: str,
        brand_b: str,
        platform: str,
        signals_a: list[dict],
        signals_b: list[dict],
    ) -> CompetitorReport:
        input_hash = self._hash({
            "a": brand_a, "b": brand_b, "platform": platform,
            "sa": signals_a, "sb": signals_b,
        })

        start = time.monotonic()
        cached = self._get_cached(f"competitor:{input_hash}")
        if cached:
            return CompetitorReport.model_validate(cached)

        def _fmt(brand: str, signals: list[dict]) -> str:
            return f"{brand}:\n" + "\n".join(
                f"  [{s.get('platform')}] eng={s.get('engagements', 0)} "
                f"strength={s.get('signal_strength', 0):.2f} — {s['post_text'][:120]}"
                for s in signals[:10]
            )

        message = await self._call_llm(
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Platform: {platform}\n\n"
                    f"{_fmt(brand_a, signals_a)}\n\n"
                    f"{_fmt(brand_b, signals_b)}\n\n"
                    f"Compare {brand_a} vs {brand_b} on: engagement, sentiment, "
                    f"topic diversity, virality, and overall strategic position."
                ),
            }],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "compare_competitors"},
        )

        raw = self._extract_tool_input(message)
        report = CompetitorReport.model_validate(raw)
        self._set_cached(f"competitor:{input_hash}", report.model_dump())
        return report
