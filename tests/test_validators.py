"""Tests for pipeline validators."""
from __future__ import annotations

import pytest

from pipeline.validators import (
    PipelineValidationError,
    validate_extracted_signals,
    validate_raw_signals,
    validate_topic_clusters,
)


class TestValidateRawSignals:
    def test_passes_valid_signals(self):
        signals = [
            {"platform": "twitter", "brand": "Nike", "post_text": "Great shoes!"},
        ]
        validate_raw_signals(signals)  # should not raise

    def test_raises_on_missing_platform(self):
        with pytest.raises(PipelineValidationError, match="platform"):
            validate_raw_signals([{"brand": "Nike", "post_text": "text"}])

    def test_raises_on_empty_post_text(self):
        with pytest.raises(PipelineValidationError, match="empty post_text"):
            validate_raw_signals([{"platform": "twitter", "brand": "Nike", "post_text": "   "}])

    def test_raises_on_multiple_missing_fields(self):
        with pytest.raises(PipelineValidationError):
            validate_raw_signals([{"platform": "twitter"}])


class TestValidateExtractedSignals:
    def test_passes_valid_extracted(self):
        signals = [
            {
                "brand": "Nike",
                "platform": "twitter",
                "sentiment": "positive",
                "trend_score": 0.85,
                "topics": [],
                "key_phrases": [],
            }
        ]
        validate_extracted_signals(signals)

    def test_raises_on_invalid_sentiment(self):
        with pytest.raises(PipelineValidationError, match="sentiment"):
            validate_extracted_signals([{"sentiment": "angry", "trend_score": 0.5}])

    def test_raises_on_trend_score_out_of_range(self):
        with pytest.raises(PipelineValidationError, match="trend_score"):
            validate_extracted_signals([{"sentiment": "positive", "trend_score": 1.5}])

    def test_raises_on_negative_trend_score(self):
        with pytest.raises(PipelineValidationError, match="trend_score"):
            validate_extracted_signals([{"sentiment": "negative", "trend_score": -0.1}])


class TestValidateTopicClusters:
    def test_passes_valid_clusters(self):
        clusters = [
            {
                "cluster_id": "c1",
                "topic_label": "hype",
                "signals": ["sig1"],
                "dominant_sentiment": "positive",
                "engagement_weight": 0.9,
            }
        ]
        validate_topic_clusters(clusters)

    def test_raises_on_missing_cluster_id(self):
        with pytest.raises(PipelineValidationError, match="cluster_id"):
            validate_topic_clusters([{"signals": ["s1"], "engagement_weight": 0.5}])

    def test_raises_on_empty_signals(self):
        with pytest.raises(PipelineValidationError, match="no signals"):
            validate_topic_clusters([{"cluster_id": "c1", "signals": [], "engagement_weight": 0.5}])

    def test_raises_on_weight_out_of_range(self):
        with pytest.raises(PipelineValidationError, match="engagement_weight"):
            validate_topic_clusters([{"cluster_id": "c1", "signals": ["s1"], "engagement_weight": 1.5}])
