"""Tests for the pluggable cache backends."""
from __future__ import annotations

import pytest

from pipeline.cache import MemoryCache


class TestMemoryCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = MemoryCache(max_size=10)
        await cache.set("key1", {"data": 42})
        result = await cache.get("key1")
        assert result == {"data": 42}

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self):
        cache = MemoryCache(max_size=10)
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        cache = MemoryCache(max_size=3)
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.set("c", 3)

        # Access 'a' to make it recently used
        await cache.get("a")

        # Adding 'd' should evict 'b' (LRU), not 'a'
        await cache.set("d", 4)

        assert await cache.get("a") == 1
        assert await cache.get("b") is None  # evicted
        assert await cache.get("c") == 3
        assert await cache.get("d") == 4

    @pytest.mark.asyncio
    async def test_delete(self):
        cache = MemoryCache()
        await cache.set("key", "value")
        await cache.delete("key")
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_clear(self):
        cache = MemoryCache()
        await cache.set("k1", 1)
        await cache.set("k2", 2)
        await cache.clear()
        assert cache.size == 0

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self):
        cache = MemoryCache()
        await cache.set("key", "original")
        await cache.set("key", "updated")
        assert await cache.get("key") == "updated"
        assert cache.size == 1

    @pytest.mark.asyncio
    async def test_handles_complex_values(self):
        cache = MemoryCache()
        value = {
            "signals": [{"brand": "Nike", "score": 0.9}],
            "count": 5,
            "nested": {"a": [1, 2, 3]},
        }
        await cache.set("complex", value)
        assert await cache.get("complex") == value
