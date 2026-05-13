"""Composite quality scorer for evaluation results.

Takes the output of evaluation.eval.run_eval() and computes a single 0–100
quality score using weighted metric contributions.

Usage:
    from evaluation.scorer import score_pipeline_output
    report = await run_eval(pipeline_output)
    result = score_pipeline_output(report)
    print(result["quality_score"])  # e.g. 84.2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Metric weights — must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "sentiment_accuracy": 0.30,
    "topic_recall": 0.25,
    "cluster_quality": 0.20,
    "action_priority_distribution": 0.15,
    "trend_score_distribution": 0.10,
}

# Score thresholds per metric: maps raw metric value → normalised 0–1
_PASS_THRESHOLDS: dict[str, float] = {
    "sentiment_accuracy": 0.70,
    "topic_recall": 0.50,
    "cluster_quality": 1.0,   # boolean pass/fail
    "action_priority_distribution": 1.0,
    "trend_score_distribution": 1.0,
}


@dataclass
class ScoredMetric:
    name: str
    raw_value: float
    normalised: float
    weight: float
    weighted_score: float
    passed: bool


def _normalise_metric(result: dict) -> float:
    """Map a metric dict to a 0–1 continuous score."""
    metric = result.get("metric", "")
    if metric == "sentiment_accuracy":
        return min(result.get("precision", 0.0) / _PASS_THRESHOLDS[metric], 1.0)
    if metric == "topic_recall":
        return min(result.get("recall", 0.0) / _PASS_THRESHOLDS[metric], 1.0)
    if metric == "cluster_quality":
        # Score: 0.5 for meeting min clusters + 0.5 for sentiment diversity
        score = 0.5 if result.get("meets_minimum") else 0.0
        score += 0.5 if result.get("diverse_sentiments") else 0.0
        return score
    if metric == "action_priority_distribution":
        counts = result.get("counts", {})
        total = result.get("total_actions", 0)
        if total == 0:
            return 0.0
        # Reward having all three priority levels represented
        present = sum(1 for v in counts.values() if v > 0)
        return present / 3
    if metric == "trend_score_distribution":
        # Rewards variance up to 0.1 — beyond that it's fully scored
        variance = result.get("variance", 0.0)
        return min(variance / 0.1, 1.0)
    return 0.0


def score_pipeline_output(eval_report: dict[str, Any]) -> dict[str, Any]:
    """Compute composite quality score from evaluation report.

    Returns a dict with:
      - quality_score: float 0–100
      - grade: letter A/B/C/D/F
      - scored_metrics: per-metric breakdown
      - summary: human-readable verdict
    """
    details: list[dict] = eval_report.get("details", [])
    scored: list[ScoredMetric] = []
    total_weight_used = 0.0
    weighted_sum = 0.0

    for result in details:
        metric_name = result.get("metric", "")
        weight = _WEIGHTS.get(metric_name, 0.0)
        if weight == 0.0:
            continue
        normalised = _normalise_metric(result)
        weighted_score = normalised * weight
        weighted_sum += weighted_score
        total_weight_used += weight
        scored.append(ScoredMetric(
            name=metric_name,
            raw_value=normalised,
            normalised=round(normalised, 3),
            weight=weight,
            weighted_score=round(weighted_score, 4),
            passed=normalised >= 0.7,
        ))

    # Normalise to full weight coverage in case some metrics are missing
    if total_weight_used > 0:
        quality_score = round((weighted_sum / total_weight_used) * 100, 1)
    else:
        quality_score = 0.0

    grade = _letter_grade(quality_score)

    return {
        "quality_score": quality_score,
        "grade": grade,
        "total_weight_used": round(total_weight_used, 2),
        "scored_metrics": [
            {
                "metric": s.name,
                "normalised": s.normalised,
                "weight": s.weight,
                "weighted_score": s.weighted_score,
                "passed": s.passed,
            }
            for s in scored
        ],
        "summary": _verdict(quality_score, scored),
    }


def _letter_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _verdict(score: float, metrics: list[ScoredMetric]) -> str:
    failed_names = [m.name for m in metrics if not m.passed]
    if score >= 85:
        return "Pipeline output meets production quality standards."
    if score >= 70:
        weak = ", ".join(failed_names) if failed_names else "minor areas"
        return f"Acceptable quality — improve: {weak}."
    return f"Quality below threshold — failing metrics: {', '.join(failed_names) or 'multiple'}."
