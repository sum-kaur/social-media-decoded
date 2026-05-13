"""Tests for the batch pipeline runner."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pipeline.batch import BatchJob, BatchResult, run_batch


def _make_final_state(brand: str, success: bool = True) -> dict:
    return {
        "run_id": f"run-{brand}",
        "brand": brand,
        "platform": "twitter",
        "completed_agents": ["signal_extractor", "topic_clusterer", "insight_generator", "action_recommender"],
        "insight_id": "abc-123" if success else None,
        "error": None if success else "LLM rate limit",
    }


SAMPLE_SIGNALS = [
    {
        "id": "sig1",
        "platform": "twitter",
        "brand": "Nike",
        "post_text": "Great product!",
        "ingested_at": None,
    }
]


class TestRunBatch:
    @pytest.mark.asyncio
    async def test_runs_all_jobs(self):
        jobs = [
            BatchJob(brand="Nike", platform="twitter"),
            BatchJob(brand="Adidas", platform="instagram"),
        ]

        async def mock_get_signals(brand, limit=50):
            return [dict(SAMPLE_SIGNALS[0], brand=brand)]

        async def mock_pipeline(brand, platform, signal_ids, raw_signals):
            return _make_final_state(brand)

        with patch("pipeline.batch.queries.get_signals_by_brand", side_effect=mock_get_signals):
            with patch("pipeline.batch.run_pipeline", side_effect=mock_pipeline):
                results = await run_batch(jobs, concurrency=2)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert {r.brand for r in results} == {"Nike", "Adidas"}

    @pytest.mark.asyncio
    async def test_handles_empty_signals_gracefully(self):
        jobs = [BatchJob(brand="UnknownBrand", platform="twitter")]

        with patch("pipeline.batch.queries.get_signals_by_brand", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = []
            results = await run_batch(jobs)

        assert len(results) == 1
        assert not results[0].success
        assert results[0].error == "No signals found"

    @pytest.mark.asyncio
    async def test_handles_pipeline_exception(self):
        jobs = [BatchJob(brand="ErrorBrand", platform="twitter")]

        with patch("pipeline.batch.queries.get_signals_by_brand", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = [dict(SAMPLE_SIGNALS[0])]
            with patch("pipeline.batch.run_pipeline", side_effect=RuntimeError("API down")):
                results = await run_batch(jobs)

        assert not results[0].success
        assert "API down" in results[0].error

    @pytest.mark.asyncio
    async def test_concurrency_limit_respected(self):
        """Verify semaphore allows at most `concurrency` jobs to run simultaneously."""
        import asyncio
        active = []
        max_concurrent = 0

        jobs = [BatchJob(brand=f"Brand{i}", platform="twitter") for i in range(6)]

        async def mock_get_signals(brand, limit=50):
            return [dict(SAMPLE_SIGNALS[0], brand=brand)]

        async def mock_pipeline(brand, platform, signal_ids, raw_signals):
            nonlocal max_concurrent
            active.append(brand)
            max_concurrent = max(max_concurrent, len(active))
            await asyncio.sleep(0.01)
            active.remove(brand)
            return _make_final_state(brand)

        with patch("pipeline.batch.queries.get_signals_by_brand", side_effect=mock_get_signals):
            with patch("pipeline.batch.run_pipeline", side_effect=mock_pipeline):
                await run_batch(jobs, concurrency=2)

        assert max_concurrent <= 2
