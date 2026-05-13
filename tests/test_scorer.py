"""Tests for the evaluation quality scorer."""
from __future__ import annotations

import pytest

from evaluation.scorer import score_pipeline_output


def _make_eval_report(details: list[dict]) -> dict:
    passed = sum(1 for d in details if d.get("precision", d.get("recall", 1.0)) >= 0.7)
    return {
        "total_checks": len(details),
        "passed": passed,
        "failed": len(details) - passed,
        "pass_rate": passed / len(details) if details else 0.0,
        "details": details,
    }


class TestScorer:
    def test_perfect_output_scores_100(self):
        report = _make_eval_report([
            {"metric": "sentiment_accuracy", "precision": 1.0},
            {"metric": "topic_recall", "recall": 1.0},
            {"metric": "cluster_quality", "meets_minimum": True, "diverse_sentiments": True},
            {"metric": "action_priority_distribution", "counts": {"high": 2, "medium": 2, "low": 2}, "total_actions": 6},
            {"metric": "trend_score_distribution", "variance": 0.15},
        ])
        result = score_pipeline_output(report)
        assert result["quality_score"] == 100.0
        assert result["grade"] == "A"

    def test_all_zero_output_scores_0(self):
        report = _make_eval_report([
            {"metric": "sentiment_accuracy", "precision": 0.0},
            {"metric": "topic_recall", "recall": 0.0},
            {"metric": "cluster_quality", "meets_minimum": False, "diverse_sentiments": False},
            {"metric": "action_priority_distribution", "counts": {"high": 0, "medium": 0, "low": 0}, "total_actions": 0},
            {"metric": "trend_score_distribution", "variance": 0.0},
        ])
        result = score_pipeline_output(report)
        assert result["quality_score"] == 0.0
        assert result["grade"] == "F"

    def test_grade_boundaries(self):
        cases = [
            (95.0, "A"),
            (85.0, "B"),
            (75.0, "C"),
            (65.0, "D"),
            (50.0, "F"),
        ]
        for score, expected_grade in cases:
            # Build a report that hits exactly this score via sentiment_accuracy only
            prec = score / 100.0
            report = _make_eval_report([
                {"metric": "sentiment_accuracy", "precision": prec},
            ])
            result = score_pipeline_output(report)
            assert result["grade"] == expected_grade, f"score={score} expected {expected_grade}, got {result['grade']}"

    def test_empty_report_returns_zero(self):
        result = score_pipeline_output({"details": []})
        assert result["quality_score"] == 0.0

    def test_partial_metrics_normalise_to_available_weight(self):
        report = _make_eval_report([
            {"metric": "sentiment_accuracy", "precision": 1.0},
        ])
        result = score_pipeline_output(report)
        # Only sentiment_accuracy (weight=0.30) — normalised → still 100
        assert result["quality_score"] == 100.0
        assert result["total_weight_used"] == 0.30

    def test_summary_mentions_failing_metrics(self):
        report = _make_eval_report([
            {"metric": "sentiment_accuracy", "precision": 0.3},
            {"metric": "topic_recall", "recall": 0.2},
        ])
        result = score_pipeline_output(report)
        assert "sentiment_accuracy" in result["summary"] or "topic_recall" in result["summary"]

    def test_scored_metrics_structure(self):
        report = _make_eval_report([
            {"metric": "sentiment_accuracy", "precision": 0.8},
        ])
        result = score_pipeline_output(report)
        assert len(result["scored_metrics"]) == 1
        m = result["scored_metrics"][0]
        assert "metric" in m
        assert "normalised" in m
        assert "weight" in m
        assert "weighted_score" in m
        assert "passed" in m

    def test_cluster_quality_partial_score(self):
        # Only meets_minimum but no sentiment diversity → 0.5 normalised
        report = _make_eval_report([
            {"metric": "cluster_quality", "meets_minimum": True, "diverse_sentiments": False},
        ])
        result = score_pipeline_output(report)
        sm = result["scored_metrics"][0]
        assert sm["normalised"] == 0.5
        assert sm["passed"] is False
