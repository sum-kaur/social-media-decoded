"""
Batch pipeline runner — process multiple brands concurrently.

Useful for scheduled nightly jobs that refresh insights for all active brands.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from pipeline.orchestrator import run_pipeline
from db import queries

logger = logging.getLogger(__name__)


@dataclass
class BatchJob:
    brand: str
    platform: str
    signal_limit: int = 50


@dataclass
class BatchResult:
    brand: str
    platform: str
    success: bool
    insight_id: str | None
    agents_completed: list[str]
    error: str | None


async def _run_single(job: BatchJob) -> BatchResult:
    try:
        raw_signals = await queries.get_signals_by_brand(job.brand, limit=job.signal_limit)
        if not raw_signals:
            return BatchResult(
                brand=job.brand, platform=job.platform,
                success=False, insight_id=None,
                agents_completed=[], error="No signals found",
            )

        signal_ids = [str(s["id"]) for s in raw_signals]
        signals_dicts = []
        for s in raw_signals:
            d = dict(s)
            d["id"] = str(d["id"])
            if d.get("ingested_at"):
                d["ingested_at"] = d["ingested_at"].isoformat()
            signals_dicts.append(d)

        final_state = await run_pipeline(
            brand=job.brand,
            platform=job.platform,
            signal_ids=signal_ids,
            raw_signals=signals_dicts,
        )

        return BatchResult(
            brand=job.brand,
            platform=job.platform,
            success=not final_state.get("error"),
            insight_id=final_state.get("insight_id"),
            agents_completed=final_state.get("completed_agents", []),
            error=final_state.get("error"),
        )
    except Exception as exc:
        logger.exception("Batch job failed for brand=%s", job.brand)
        return BatchResult(
            brand=job.brand, platform=job.platform,
            success=False, insight_id=None,
            agents_completed=[], error=str(exc),
        )


async def run_batch(
    jobs: list[BatchJob],
    concurrency: int = 3,
) -> list[BatchResult]:
    """
    Run multiple pipeline jobs with bounded concurrency.

    Uses a semaphore to avoid overwhelming the Anthropic API with
    simultaneous requests from many brands.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded(job: BatchJob) -> BatchResult:
        async with semaphore:
            logger.info("Batch: starting brand=%s platform=%s", job.brand, job.platform)
            result = await _run_single(job)
            status = "ok" if result.success else f"failed: {result.error}"
            logger.info("Batch: finished brand=%s → %s", job.brand, status)
            return result

    results = await asyncio.gather(*[_bounded(j) for j in jobs])

    succeeded = sum(1 for r in results if r.success)
    logger.info("Batch complete: %d/%d succeeded", succeeded, len(jobs))
    return list(results)
