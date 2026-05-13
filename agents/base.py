"""Shared base class and utilities for all pipeline agents."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import anthropic

from pipeline.retry import CircuitBreaker, with_exponential_backoff

logger = logging.getLogger(__name__)

# In-memory response cache — swap for Redis in production
_response_cache: dict[str, Any] = {}

_anthropic_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)


def _hash_input(data: Any) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


class BaseAgent:
    MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")
    MAX_TOKENS = 4096

    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic()
        self.name: str = self.__class__.__name__

    @with_exponential_backoff(
        max_retries=int(os.environ.get("LLM_MAX_RETRIES", "3")),
        base_delay=float(os.environ.get("LLM_RETRY_BASE_DELAY", "1.0")),
        retryable_exceptions=(anthropic.RateLimitError, anthropic.APIStatusError),
    )
    async def _call_llm(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        tool_choice: dict | None = None,
    ) -> anthropic.types.Message:
        return await _anthropic_circuit_breaker.call(
            self.client.messages.create,
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=system,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice or {"type": "any"},
        )

    async def run(self, state: dict) -> dict:
        """Override in subclasses."""
        raise NotImplementedError

    def _get_cached(self, input_hash: str) -> Any | None:
        return _response_cache.get(input_hash)

    def _set_cached(self, input_hash: str, value: Any) -> None:
        # LRU eviction: drop oldest entry when cache exceeds 512 items
        if len(_response_cache) >= 512:
            oldest = next(iter(_response_cache))
            del _response_cache[oldest]
        _response_cache[input_hash] = value

    def _build_trace_entry(
        self,
        input_hash: str,
        output: Any,
        latency_ms: float,
        token_count: int,
        error: str | None = None,
    ) -> dict:
        return {
            "agent_name": self.name,
            "input_hash": input_hash,
            "output": output,
            "latency_ms": latency_ms,
            "token_count": token_count,
            "error": error,
        }

    @staticmethod
    def _hash(data: Any) -> str:
        return _hash_input(data)

    @staticmethod
    def _extract_tool_input(message: anthropic.types.Message) -> dict:
        for block in message.content:
            if block.type == "tool_use":
                return block.input  # type: ignore[return-value]
        raise ValueError("No tool_use block found in LLM response")
