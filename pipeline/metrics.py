"""
Lightweight in-process metrics collection.

Tracks agent call counts, error rates, and p50/p99 latencies.
Exposed via GET /metrics (Prometheus text format) in production.
"""
from __future__ import annotations

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class AgentMetrics:
    call_count: int = 0
    error_count: int = 0
    cache_hits: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    def record_call(self, latency_ms: float, cache_hit: bool = False, error: bool = False) -> None:
        self.call_count += 1
        if error:
            self.error_count += 1
        if cache_hit:
            self.cache_hits += 1
        self.latencies_ms.append(latency_ms)
        # Keep only last 1000 samples to bound memory
        if len(self.latencies_ms) > 1000:
            self.latencies_ms = self.latencies_ms[-1000:]

    @property
    def p50_ms(self) -> float | None:
        if not self.latencies_ms:
            return None
        return statistics.median(self.latencies_ms)

    @property
    def p99_ms(self) -> float | None:
        if len(self.latencies_ms) < 2:
            return None
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * 0.99)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    @property
    def error_rate(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.error_count / self.call_count


class MetricsRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentMetrics] = defaultdict(AgentMetrics)
        self._lock = Lock()

    def record(
        self,
        agent_name: str,
        latency_ms: float,
        cache_hit: bool = False,
        error: bool = False,
    ) -> None:
        with self._lock:
            self._agents[agent_name].record_call(latency_ms, cache_hit, error)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                name: {
                    "call_count": m.call_count,
                    "error_count": m.error_count,
                    "cache_hits": m.cache_hits,
                    "error_rate": round(m.error_rate, 4),
                    "p50_ms": round(m.p50_ms, 1) if m.p50_ms else None,
                    "p99_ms": round(m.p99_ms, 1) if m.p99_ms else None,
                }
                for name, m in self._agents.items()
            }

    def to_prometheus(self) -> str:
        lines = ["# HELP smd_agent_calls_total Total agent invocations"]
        for name, m in self._agents.items():
            lines.append(f'smd_agent_calls_total{{agent="{name}"}} {m.call_count}')
            lines.append(f'smd_agent_errors_total{{agent="{name}"}} {m.error_count}')
            lines.append(f'smd_agent_cache_hits_total{{agent="{name}"}} {m.cache_hits}')
            if m.p50_ms is not None:
                lines.append(f'smd_agent_latency_p50_ms{{agent="{name}"}} {m.p50_ms:.1f}')
            if m.p99_ms is not None:
                lines.append(f'smd_agent_latency_p99_ms{{agent="{name}"}} {m.p99_ms:.1f}')
        return "\n".join(lines) + "\n"


# Global singleton
_registry = MetricsRegistry()


def get_registry() -> MetricsRegistry:
    return _registry
