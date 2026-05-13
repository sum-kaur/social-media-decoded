"""Token-bucket rate limiter for per-brand pipeline invocations.

Prevents runaway batch jobs from monopolising the Anthropic API quota.
Each brand gets an independent bucket; bursts up to `burst` requests then
refills at `rate` tokens/second.

Usage:
    from pipeline.rate_limiter import get_limiter

    limiter = get_limiter()
    await limiter.acquire("Nike")   # blocks until a token is available
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    rate: float          # tokens refilled per second
    burst: float         # maximum token capacity
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.tokens = self.burst
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                wait_for = (1.0 - self.tokens) / self.rate
            await asyncio.sleep(wait_for)


class RateLimiter:
    def __init__(self, rate: float = 1.0, burst: float = 3.0) -> None:
        self._rate = rate
        self._burst = burst
        self._buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(rate=self._rate, burst=self._burst)
        )

    async def acquire(self, key: str) -> None:
        """Block until a token is available for `key`."""
        await self._buckets[key].acquire()

    def reset(self, key: str) -> None:
        """Reset the bucket for `key` (useful in tests)."""
        if key in self._buckets:
            del self._buckets[key]

    @property
    def active_keys(self) -> list[str]:
        return list(self._buckets.keys())


# Process-level singleton — 1 run/sec per brand, burst of 3
_limiter = RateLimiter(rate=1.0, burst=3.0)


def get_limiter() -> RateLimiter:
    return _limiter
