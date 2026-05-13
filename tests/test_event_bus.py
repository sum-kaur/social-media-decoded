"""Tests for the pipeline async event bus."""
from __future__ import annotations

import asyncio

import pytest

from pipeline.event_bus import EventBus


@pytest.fixture
def bus():
    return EventBus()


class TestEventBus:
    @pytest.mark.asyncio
    async def test_emit_calls_subscriber(self, bus):
        received = []

        async def handler(payload):
            received.append(payload)

        bus.subscribe("test.event", handler)
        await bus.emit("test.event", {"key": "value"})

        assert len(received) == 1
        assert received[0]["key"] == "value"

    @pytest.mark.asyncio
    async def test_emit_calls_multiple_subscribers(self, bus):
        calls = []

        async def handler_a(payload):
            calls.append("a")

        async def handler_b(payload):
            calls.append("b")

        bus.subscribe("multi.event", handler_a)
        bus.subscribe("multi.event", handler_b)
        await bus.emit("multi.event", {})

        assert set(calls) == {"a", "b"}

    @pytest.mark.asyncio
    async def test_emit_no_subscribers_is_noop(self, bus):
        # Should not raise even with no subscribers
        await bus.emit("unsubscribed.event", {"data": 1})

    @pytest.mark.asyncio
    async def test_failing_handler_does_not_crash_bus(self, bus):
        async def bad_handler(payload):
            raise RuntimeError("handler exploded")

        good_calls = []

        async def good_handler(payload):
            good_calls.append(True)

        bus.subscribe("mixed.event", bad_handler)
        bus.subscribe("mixed.event", good_handler)

        # Should not raise; good_handler still called
        await bus.emit("mixed.event", {})
        assert good_calls == [True]

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_handler(self, bus):
        calls = []

        async def handler(payload):
            calls.append(True)

        bus.subscribe("remove.event", handler)
        bus.unsubscribe("remove.event", handler)
        await bus.emit("remove.event", {})

        assert calls == []

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler_is_safe(self, bus):
        async def handler(payload):
            pass

        bus.unsubscribe("never.subscribed", handler)  # must not raise

    def test_event_names_tracks_subscribed_events(self, bus):
        async def noop(payload):
            pass

        bus.subscribe("event.a", noop)
        bus.subscribe("event.b", noop)

        assert set(bus.event_names) == {"event.a", "event.b"}

    @pytest.mark.asyncio
    async def test_emit_passes_correct_payload(self, bus):
        received = {}

        async def handler(payload):
            received.update(payload)

        bus.subscribe("payload.test", handler)
        await bus.emit("payload.test", {"run_id": "abc", "brand": "Nike"})

        assert received["run_id"] == "abc"
        assert received["brand"] == "Nike"
