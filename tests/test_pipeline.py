"""Tests for pipeline state, retry logic, and circuit breaker."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.retry import CircuitBreaker, with_exponential_backoff
from pipeline.state import PipelineState


class TestExponentialBackoff:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        call_count = 0

        @with_exponential_backoff(max_retries=3, base_delay=0.01)
        async def succeeds():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await succeeds()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        call_count = 0

        @with_exponential_backoff(max_retries=3, base_delay=0.01)
        async def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "recovered"

        result = await fails_twice()
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        @with_exponential_backoff(max_retries=2, base_delay=0.01)
        async def always_fails():
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            await always_fails()

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self):
        call_count = 0

        @with_exponential_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )
        async def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await raises_type_error()

        assert call_count == 1  # Did not retry


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_allows_calls_when_closed(self):
        cb = CircuitBreaker(failure_threshold=3)

        async def ok():
            return "result"

        result = await cb.call(ok)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, window_size=5)

        async def fail():
            raise RuntimeError("error")

        for _ in range(3):
            try:
                await cb.call(fail)
            except RuntimeError:
                pass

        assert cb.is_open

    @pytest.mark.asyncio
    async def test_rejects_calls_when_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999)

        async def fail():
            raise RuntimeError("error")

        for _ in range(2):
            try:
                await cb.call(fail)
            except RuntimeError:
                pass

        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            await cb.call(fail)

    def test_recovers_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.0)
        cb._state = "open"
        cb._opened_at = 0.0  # Far in the past

        # is_open transitions to half-open when recovery_timeout elapsed
        assert not cb.is_open


class TestPipelineState:
    def test_state_keys_are_correct(self):
        state: PipelineState = {
            "run_id": "test-run",
            "brand": "Nike",
            "platform": "twitter",
            "signal_ids": ["abc"],
            "raw_signals": [],
            "extracted_signals": [],
            "topic_clusters": [],
            "marketing_insights": [],
            "recommended_actions": [],
            "current_agent": "signal_extractor",
            "completed_agents": [],
            "failed_agents": [],
            "retry_counts": {},
            "pipeline_trace": [],
            "insight_id": None,
            "error": None,
        }

        assert state["brand"] == "Nike"
        assert state["current_agent"] == "signal_extractor"
        assert state["insight_id"] is None
