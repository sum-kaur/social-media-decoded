"""Unit tests for TrendAnalyzerAgent."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.trend_analyzer import TrendAnalyzerAgent


def _make_mock_message(tool_input: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.input = tool_input
    msg = MagicMock()
    msg.content = [block]
    msg.usage.input_tokens = 100
    msg.usage.output_tokens = 300
    return msg


SAMPLE_SIGNALS = [
    {
        "id": "sig1",
        "platform": "twitter",
        "brand": "Nike",
        "topics": ["product_launch", "sneakers"],
        "sentiment": "positive",
        "engagements": 45000,
        "ingested_at": "2026-05-01T10:00:00",
    },
    {
        "id": "sig2",
        "platform": "twitter",
        "brand": "Nike",
        "topics": ["sustainability", "criticism"],
        "sentiment": "negative",
        "engagements": 3400,
        "ingested_at": "2026-05-03T14:00:00",
    },
    {
        "id": "sig3",
        "platform": "twitter",
        "brand": "Nike",
        "topics": ["product_launch", "viral"],
        "sentiment": "positive",
        "engagements": 892000,
        "ingested_at": "2026-05-07T09:00:00",
    },
]

MOCK_TREND_REPORT = {
    "brand": "Nike",
    "rising_topics": [
        {
            "brand": "Nike",
            "platform": "twitter",
            "topic": "product_launch",
            "direction": "rising",
            "momentum_score": 0.85,
            "evidence": ["45k → 892k engagements in 6 days"],
        }
    ],
    "declining_topics": [
        {
            "brand": "Nike",
            "platform": "twitter",
            "topic": "sustainability",
            "direction": "declining",
            "momentum_score": -0.3,
            "evidence": ["Low engagement, negative sentiment"],
        }
    ],
    "stable_topics": [],
    "overall_momentum": 0.6,
    "analysis_period": "last 7 days",
}


class TestTrendAnalyzerAgent:
    @pytest.mark.asyncio
    async def test_returns_trend_report(self):
        mock_msg = _make_mock_message(MOCK_TREND_REPORT)

        with patch.object(TrendAnalyzerAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_msg
            agent = TrendAnalyzerAgent()
            report = await agent.run_trend_analysis(
                brand="Nike",
                platform="twitter",
                signals=SAMPLE_SIGNALS,
            )

        assert report.brand == "Nike"
        assert len(report.rising_topics) == 1
        assert report.rising_topics[0].topic == "product_launch"
        assert report.overall_momentum == 0.6

    @pytest.mark.asyncio
    async def test_momentum_score_bounds(self):
        mock_msg = _make_mock_message(MOCK_TREND_REPORT)

        with patch.object(TrendAnalyzerAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_msg
            agent = TrendAnalyzerAgent()
            report = await agent.run_trend_analysis(
                brand="Nike",
                platform="twitter",
                signals=SAMPLE_SIGNALS,
            )

        for signal in report.rising_topics + report.declining_topics + report.stable_topics:
            assert -1 <= signal.momentum_score <= 1

    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm(self):
        mock_msg = _make_mock_message(MOCK_TREND_REPORT)

        with patch.object(TrendAnalyzerAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_msg
            agent = TrendAnalyzerAgent()

            # First call
            await agent.run_trend_analysis("Nike", "twitter", SAMPLE_SIGNALS)
            # Second call — same input
            await agent.run_trend_analysis("Nike", "twitter", SAMPLE_SIGNALS)

            # LLM called only once
            assert mock_llm.call_count == 1
