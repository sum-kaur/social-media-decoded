"""Tests for the per-brand token-bucket rate limiter."""
from __future__ import annotations

import asyncio
import time

import pytest

from pipeline.rate_limiter import RateLimiter


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_burst_tokens_consumed_immediately(self):
        limiter = RateLimiter(rate=1.0, burst=3.0)
        start = time.monotonic()
        for _ in range(3):
            await limiter.acquire("Nike")
        elapsed = time.monotonic() - start
        # All 3 burst tokens should be consumed near-instantly
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_beyond_burst_incurs_delay(self):
        limiter = RateLimiter(rate=10.0, burst=2.0)  # fast refill for test speed
        for _ in range(2):
            await limiter.acquire("Nike")
        start = time.monotonic()
        await limiter.acquire("Nike")
        elapsed = time.monotonic() - start
        # Third token requires refill — should take ~0.1s at rate=10
        assert elapsed > 0.05

    @pytest.mark.asyncio
    async def test_independent_buckets_per_key(self):
        limiter = RateLimiter(rate=1.0, burst=1.0)
        start = time.monotonic()
        await limiter.acquire("Nike")
        await limiter.acquire("Adidas")
        elapsed = time.monotonic() - start
        # Different brands use independent buckets — both should complete fast
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_reset_restores_full_bucket(self):
        limiter = RateLimiter(rate=0.01, burst=1.0)  # very slow refill
        await limiter.acquire("Nike")
        limiter.reset("Nike")

        start = time.monotonic()
        await limiter.acquire("Nike")  # should succeed immediately after reset
        elapsed = time.monotonic() - start
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_active_keys_tracks_used_buckets(self):
        limiter = RateLimiter(rate=1.0, burst=5.0)
        await limiter.acquire("BrandA")
        await limiter.acquire("BrandB")
        assert "BrandA" in limiter.active_keys
        assert "BrandB" in limiter.active_keys

    @pytest.mark.asyncio
    async def test_concurrent_acquires_serialise_per_key(self):
        limiter = RateLimiter(rate=100.0, burst=5.0)  # high rate for test speed
        results = []

        async def worker(i: int):
            await limiter.acquire("shared_key")
            results.append(i)

        await asyncio.gather(*[worker(i) for i in range(5)])
        assert len(results) == 5
