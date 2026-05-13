"""Tests for the metrics registry."""
from __future__ import annotations

import pytest

from pipeline.metrics import AgentMetrics, MetricsRegistry


class TestAgentMetrics:
    def test_records_call(self):
        m = AgentMetrics()
        m.record_call(latency_ms=120.0)
        assert m.call_count == 1
        assert m.error_count == 0
        assert m.cache_hits == 0

    def test_records_error(self):
        m = AgentMetrics()
        m.record_call(100.0, error=True)
        assert m.error_count == 1
        assert m.error_rate == 1.0

    def test_records_cache_hit(self):
        m = AgentMetrics()
        m.record_call(5.0, cache_hit=True)
        assert m.cache_hits == 1

    def test_p50_single_sample(self):
        m = AgentMetrics()
        m.record_call(200.0)
        assert m.p50_ms == 200.0

    def test_p50_multiple_samples(self):
        m = AgentMetrics()
        for ms in [100, 200, 300, 400, 500]:
            m.record_call(float(ms))
        assert m.p50_ms == 300.0

    def test_p99_bounds(self):
        m = AgentMetrics()
        for i in range(100):
            m.record_call(float(i))
        assert m.p99_ms is not None
        assert m.p99_ms >= 98.0

    def test_error_rate_zero_calls(self):
        m = AgentMetrics()
        assert m.error_rate == 0.0

    def test_latency_buffer_capped_at_1000(self):
        m = AgentMetrics()
        for i in range(1200):
            m.record_call(float(i))
        assert len(m.latencies_ms) == 1000


class TestMetricsRegistry:
    def test_snapshot_empty(self):
        reg = MetricsRegistry()
        assert reg.snapshot() == {}

    def test_snapshot_after_record(self):
        reg = MetricsRegistry()
        reg.record("signal_extractor", 150.0)
        reg.record("signal_extractor", 200.0, cache_hit=True)
        reg.record("topic_clusterer", 80.0, error=True)

        snap = reg.snapshot()
        assert snap["signal_extractor"]["call_count"] == 2
        assert snap["signal_extractor"]["cache_hits"] == 1
        assert snap["topic_clusterer"]["error_count"] == 1
        assert snap["topic_clusterer"]["error_rate"] == 1.0

    def test_prometheus_format(self):
        reg = MetricsRegistry()
        reg.record("signal_extractor", 120.0)
        output = reg.to_prometheus()
        assert "smd_agent_calls_total" in output
        assert 'agent="signal_extractor"' in output
