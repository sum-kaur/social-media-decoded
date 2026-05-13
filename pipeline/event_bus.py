"""Lightweight in-process async event bus for pipeline lifecycle hooks.

Subscribers register callables against event names. The bus calls each
subscriber concurrently and logs failures without crashing the pipeline.

Usage:
    from pipeline.event_bus import get_bus

    bus = get_bus()
    bus.subscribe("pipeline.completed", my_async_handler)
    await bus.emit("pipeline.completed", {"brand": "Nike", "insight_id": "..."})
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event: str, handler: Handler) -> None:
        self._subscribers[event].append(handler)
        logger.debug("Subscribed %s to event '%s'", handler.__name__, event)

    def unsubscribe(self, event: str, handler: Handler) -> None:
        try:
            self._subscribers[event].remove(handler)
        except ValueError:
            pass

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        handlers = self._subscribers.get(event, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *[h(payload) for h in handlers],
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.warning(
                    "Event handler %s failed for '%s': %s",
                    handler.__name__, event, result,
                )

    @property
    def event_names(self) -> list[str]:
        return list(self._subscribers.keys())


# Process-level singleton
_bus = EventBus()


def get_bus() -> EventBus:
    return _bus
