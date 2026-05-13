"""Input validation for pipeline state transitions."""
from __future__ import annotations

from typing import Any


class PipelineValidationError(ValueError):
    pass


def validate_raw_signals(signals: list[dict]) -> None:
    """Raise PipelineValidationError if any signal is missing required fields."""
    required = {"platform", "brand", "post_text"}
    for i, signal in enumerate(signals):
        missing = required - set(signal.keys())
        if missing:
            raise PipelineValidationError(
                f"Signal at index {i} missing required fields: {sorted(missing)}"
            )
        if not signal["post_text"].strip():
            raise PipelineValidationError(f"Signal at index {i} has empty post_text")


def validate_extracted_signals(signals: list[dict]) -> None:
    """Ensure each extracted signal has valid sentiment and trend_score bounds."""
    valid_sentiments = {"positive", "negative", "neutral"}
    for i, signal in enumerate(signals):
        sentiment = signal.get("sentiment", "")
        if sentiment not in valid_sentiments:
            raise PipelineValidationError(
                f"Extracted signal {i} has invalid sentiment '{sentiment}'"
            )
        trend_score = signal.get("trend_score", -1)
        if not (0 <= trend_score <= 1):
            raise PipelineValidationError(
                f"Extracted signal {i} trend_score={trend_score} out of [0, 1] range"
            )


def validate_topic_clusters(clusters: list[dict]) -> None:
    """Ensure clusters have required fields and at least one signal reference."""
    for i, cluster in enumerate(clusters):
        if not cluster.get("cluster_id"):
            raise PipelineValidationError(f"Cluster {i} missing cluster_id")
        if not cluster.get("signals"):
            raise PipelineValidationError(f"Cluster {i} ({cluster.get('cluster_id')}) has no signals")
        weight = cluster.get("engagement_weight", -1)
        if not (0 <= weight <= 1):
            raise PipelineValidationError(
                f"Cluster {i} engagement_weight={weight} out of [0, 1] range"
            )
