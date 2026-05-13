"""
Precision / recall checks on agent outputs.

Run: python -m evaluation.eval
Requires ANTHROPIC_API_KEY and DATABASE_URL in environment.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> Any:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Signal extraction evaluation
# ---------------------------------------------------------------------------

def eval_sentiment_accuracy(
    extracted: list[dict],
    fixtures: list[dict],
) -> dict:
    """Compare extracted sentiment to expected sentiment in fixtures."""
    correct = 0
    total = 0
    mismatches = []

    fixture_map = {f["post_text"]: f["expected_sentiment"] for f in fixtures}

    for signal in extracted:
        post_text = signal.get("post_text", "")
        if post_text in fixture_map:
            expected = fixture_map[post_text]
            actual = signal.get("sentiment", "")
            total += 1
            if actual == expected:
                correct += 1
            else:
                mismatches.append({
                    "post_text": post_text[:80],
                    "expected": expected,
                    "actual": actual,
                })

    precision = correct / total if total > 0 else 0.0
    return {
        "metric": "sentiment_accuracy",
        "precision": precision,
        "correct": correct,
        "total": total,
        "mismatches": mismatches,
    }


def eval_topic_coverage(
    extracted: list[dict],
    fixtures: list[dict],
) -> dict:
    """Check whether extracted topics cover expected topics from fixtures."""
    total_expected = 0
    total_covered = 0

    for fixture in fixtures:
        expected_topics = set(fixture.get("expected_topics", []))
        for signal in extracted:
            if signal.get("platform") == fixture.get("platform") and \
               signal.get("brand") == fixture.get("brand"):
                extracted_topics = set(signal.get("topics", []))
                covered = expected_topics & extracted_topics
                total_expected += len(expected_topics)
                total_covered += len(covered)
                break

    recall = total_covered / total_expected if total_expected > 0 else 0.0
    return {
        "metric": "topic_recall",
        "recall": recall,
        "covered": total_covered,
        "expected": total_expected,
    }


def eval_cluster_quality(
    clusters: list[dict],
    expected_config: dict,
) -> dict:
    """Validate cluster count and theme diversity."""
    min_clusters = expected_config.get("minimum_clusters", 2)
    cluster_count = len(clusters)
    labels = [c.get("topic_label", "").lower() for c in clusters]

    has_min_clusters = cluster_count >= min_clusters
    has_diverse_sentiments = len({c.get("dominant_sentiment") for c in clusters}) > 1

    return {
        "metric": "cluster_quality",
        "cluster_count": cluster_count,
        "meets_minimum": has_min_clusters,
        "diverse_sentiments": has_diverse_sentiments,
        "topic_labels": labels,
    }


def eval_action_priority_distribution(
    actions: list[dict],
) -> dict:
    """Check that recommendations span multiple priority levels."""
    priorities = [a.get("priority", "").lower() for a in actions]
    counts = {"high": 0, "medium": 0, "low": 0}
    for p in priorities:
        if p in counts:
            counts[p] += 1

    return {
        "metric": "action_priority_distribution",
        "counts": counts,
        "has_high_priority": counts["high"] > 0,
        "total_actions": len(actions),
    }


def eval_trend_score_distribution(extracted: list[dict]) -> dict:
    """Check that trend scores are spread across the [0,1] range (not all 0 or all 1)."""
    scores = [s.get("trend_score", 0) for s in extracted]
    if not scores:
        return {"metric": "trend_score_distribution", "pass": False, "reason": "no signals"}
    avg = sum(scores) / len(scores)
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
    return {
        "metric": "trend_score_distribution",
        "avg": round(avg, 3),
        "variance": round(variance, 4),
        "has_variance": variance > 0.01,
    }


async def run_eval(pipeline_output: dict) -> dict:
    """Run all evaluation checks on a completed pipeline output."""
    fixtures = _load_json("sample_signals.json")
    expected_clusters = _load_json("expected_clusters.json")

    results = []

    if pipeline_output.get("extracted_signals"):
        results.append(eval_sentiment_accuracy(
            pipeline_output["extracted_signals"], fixtures,
        ))
        results.append(eval_topic_coverage(
            pipeline_output["extracted_signals"], fixtures,
        ))
        results.append(eval_trend_score_distribution(
            pipeline_output["extracted_signals"],
        ))

    if pipeline_output.get("topic_clusters"):
        results.append(eval_cluster_quality(
            pipeline_output["topic_clusters"], expected_clusters,
        ))

    if pipeline_output.get("recommended_actions"):
        results.append(eval_action_priority_distribution(
            pipeline_output["recommended_actions"],
        ))

    passed = sum(1 for r in results if _result_passes(r))

    return {
        "total_checks": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "details": results,
    }


def _result_passes(result: dict) -> bool:
    metric = result.get("metric", "")
    if metric == "sentiment_accuracy":
        return result.get("precision", 0) >= 0.7
    if metric == "topic_recall":
        return result.get("recall", 0) >= 0.5
    if metric == "cluster_quality":
        return result.get("meets_minimum", False)
    if metric == "action_priority_distribution":
        return result.get("has_high_priority", False)
    if metric == "trend_score_distribution":
        return result.get("has_variance", False)
    return True


if __name__ == "__main__":
    print("Evaluation module ready. Invoke via run_eval(pipeline_output) after running the pipeline.")
    print(f"Fixtures at: {FIXTURES_DIR}")
