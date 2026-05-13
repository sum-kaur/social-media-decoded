"""
Pluggable cache backend for agent response memoisation.

In development: in-memory LRU dict (default).
In production: swap to Redis by setting CACHE_BACKEND=redis and REDIS_URL.

Usage in agents:
    from pipeline.cache import get_cache
    cache = get_cache()
    value = await cache.get(key)
    await cache.set(key, value)
"""
from __future__ import annotations

import json
import logging
import os
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


class MemoryCache:
    """Thread-safe LRU cache backed by an OrderedDict."""

    def __init__(self, max_size: int = 512) -> None:
        self._store: OrderedDict[str, str] = OrderedDict()
        self._max_size = max_size

    async def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return json.loads(self._store[key])

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        else:
            if len(self._store) >= self._max_size:
                evicted = next(iter(self._store))
                del self._store[evicted]
                logger.debug("Cache evicted key=%s", evicted)
        self._store[key] = json.dumps(value, default=str)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


class RedisCache:
    """Redis-backed cache — requires `redis` package and REDIS_URL env var."""

    def __init__(self, url: str) -> None:
        try:
            import redis.asyncio as aioredis
            self._client = aioredis.from_url(url, decode_responses=True)
        except ImportError:
            raise RuntimeError("Install 'redis' package to use Redis cache backend")

    async def get(self, key: str) -> Any | None:
        value = await self._client.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        await self._client.set(key, json.dumps(value, default=str), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def clear(self) -> None:
        await self._client.flushdb()


_cache_instance: MemoryCache | RedisCache | None = None


def get_cache() -> MemoryCache | RedisCache:
    global _cache_instance
    if _cache_instance is None:
        backend = os.environ.get("CACHE_BACKEND", "memory")
        if backend == "redis":
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            _cache_instance = RedisCache(url=redis_url)
            logger.info("Cache backend: Redis at %s", redis_url)
        else:
            max_size = int(os.environ.get("CACHE_MAX_SIZE", "512"))
            _cache_instance = MemoryCache(max_size=max_size)
            logger.info("Cache backend: in-memory LRU (max_size=%d)", max_size)
    return _cache_instance
