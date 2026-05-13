"""Unit tests for individual agents — LLM calls are mocked."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.action_recommender import ActionRecommenderAgent
from agents.insight_generator import InsightGeneratorAgent
from agents.signal_extractor import SignalExtractorAgent
from agents.topic_clusterer import TopicClustererAgent


def _make_mock_message(tool_input: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.input = tool_input
    msg = MagicMock()
    msg.content = [block]
    msg.usage.input_tokens = 100
    msg.usage.output_tokens = 200
    return msg


SAMPLE_SIGNALS = [
    {
        "id": "abc123",
        "platform": "twitter",
        "brand": "Nike",
        "category": "sportswear",
        "post_text": "Love the new Air Max 2025! 🔥",
        "campaign_type": "product_launch",
        "engagements": 45230,
        "signal_strength": 0.92,
    }
]

SAMPLE_EXTRACTED = [
    {
        "brand": "Nike",
        "platform": "twitter",
        "sentiment": "positive",
        "topics": ["product_launch", "sneakers"],
        "trend_score": 0.9,
        "key_phrases": ["Air Max 2025"],
    }
]

SAMPLE_CLUSTERS = [
    {
        "cluster_id": "c1",
        "topic_label": "product_hype",
        "signals": ["Nike_twitter"],
        "dominant_sentiment": "positive",
        "engagement_weight": 0.85,
    }
]

SAMPLE_INSIGHTS = [
    {
        "summary": "Strong product launch momentum",
        "what_it_means": "Air Max 2025 is resonating with core audience",
        "confidence": 0.88,
        "supporting_signals": ["Nike_twitter"],
    }
]


class TestSignalExtractorAgent:
    @pytest.mark.asyncio
    async def test_extracts_signals_from_raw_posts(self):
        mock_output = {
            "signals": [
                {
                    "brand": "Nike",
                    "platform": "twitter",
                    "sentiment": "positive",
                    "topics": ["product_launch", "sneakers"],
                    "trend_score": 0.9,
                    "key_phrases": ["Air Max 2025"],
                }
            ]
        }
        mock_msg = _make_mock_message(mock_output)

        with patch.object(SignalExtractorAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_msg
            agent = SignalExtractorAgent()
            state = {
                "raw_signals": SAMPLE_SIGNALS,
                "pipeline_trace": [],
                "completed_agents": [],
            }
            result = await agent.run(state)

        assert "extracted_signals" in result
        assert len(result["extracted_signals"]) == 1
        assert result["extracted_signals"][0]["sentiment"] == "positive"
        assert "signal_extractor" in result["completed_agents"]

    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self):
        mock_output = {
            "signals": [
                {
                    "brand": "Nike",
                    "platform": "twitter",
                    "sentiment": "positive",
                    "topics": ["sneakers"],
                    "trend_score": 0.8,
                    "key_phrases": [],
                }
            ]
        }
        mock_msg = _make_mock_message(mock_output)

        with patch.object(SignalExtractorAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_msg
            agent = SignalExtractorAgent()
            state = {"raw_signals": SAMPLE_SIGNALS, "pipeline_trace": [], "completed_agents": []}

            await agent.run(state)
            await agent.run(state)

            # LLM called only once; second call served from cache
            assert mock_llm.call_count == 1


class TestTopicClustererAgent:
    @pytest.mark.asyncio
    async def test_clusters_extracted_signals(self):
        mock_output = {
            "clusters": [
                {
                    "cluster_id": "c1",
                    "topic_label": "product_hype",
                    "signals": ["Nike_twitter"],
                    "dominant_sentiment": "positive",
                    "engagement_weight": 0.85,
                }
            ]
        }
        mock_msg = _make_mock_message(mock_output)

        with patch.object(TopicClustererAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_msg
            agent = TopicClustererAgent()
            state = {
                "extracted_signals": SAMPLE_EXTRACTED,
                "pipeline_trace": [],
                "completed_agents": [],
            }
            result = await agent.run(state)

        assert "topic_clusters" in result
        assert result["topic_clusters"][0]["topic_label"] == "product_hype"


class TestInsightGeneratorAgent:
    @pytest.mark.asyncio
    async def test_generates_marketing_insights(self):
        mock_output = {
            "insights": [
                {
                    "summary": "Strong launch signal",
                    "what_it_means": "Audience is primed for conversion",
                    "confidence": 0.9,
                    "supporting_signals": ["Nike_twitter"],
                }
            ]
        }
        mock_msg = _make_mock_message(mock_output)

        with patch.object(InsightGeneratorAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_msg
            agent = InsightGeneratorAgent()
            state = {
                "topic_clusters": SAMPLE_CLUSTERS,
                "extracted_signals": SAMPLE_EXTRACTED,
                "brand": "Nike",
                "platform": "twitter",
                "pipeline_trace": [],
                "completed_agents": [],
            }
            result = await agent.run(state)

        assert "marketing_insights" in result
        assert result["marketing_insights"][0]["confidence"] == 0.9


class TestActionRecommenderAgent:
    @pytest.mark.asyncio
    async def test_recommends_prioritised_actions(self):
        mock_output = {
            "recommendations": [
                {
                    "action": "Run retargeting campaign on Twitter",
                    "rationale": "High engagement signal from product launch",
                    "priority": "high",
                    "platform": "twitter",
                    "timeframe": "Next 7 days",
                }
            ]
        }
        mock_msg = _make_mock_message(mock_output)

        with patch.object(ActionRecommenderAgent, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_msg
            agent = ActionRecommenderAgent()
            state = {
                "marketing_insights": SAMPLE_INSIGHTS,
                "brand": "Nike",
                "platform": "twitter",
                "pipeline_trace": [],
                "completed_agents": [],
            }
            result = await agent.run(state)

        assert "recommended_actions" in result
        assert result["recommended_actions"][0]["priority"] == "high"
        assert result["current_agent"] == "done"
