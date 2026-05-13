"""Exponential backoff with jitter and a simple circuit breaker."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BASE_DELAY = 1.0
_DEFAULT_MAX_DELAY = 30.0


def with_exponential_backoff(
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
    max_delay: float = _DEFAULT_MAX_DELAY,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry async callables with exponential backoff + full jitter."""

    def decorator(fn: F) -> F:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        break
                    # Full jitter: sleep in [0, min(cap, base * 2^attempt)]
                    cap = min(max_delay, base_delay * (2 ** attempt))
                    sleep_for = random.uniform(0, cap)
                    logger.warning(
                        "Retry %d/%d for %s after %.2fs — %s: %s",
                        attempt + 1, max_retries, fn.__name__, sleep_for,
                        type(exc).__name__, exc,
                    )
                    await asyncio.sleep(sleep_for)
                except Exception as exc:
                    # Non-retryable exceptions propagate immediately
                    raise
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


class CircuitBreaker:
    """
    Half-open circuit breaker: tracks recent failures and opens the circuit
    once the failure rate exceeds a threshold within a rolling window.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        window_size: int = 10,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures: deque[float] = deque(maxlen=window_size)
        self._opened_at: float | None = None
        self._state: str = "closed"  # closed | open | half-open

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if time.monotonic() - (self._opened_at or 0) >= self.recovery_timeout:
                self._state = "half-open"
                return False
            return True
        return False

    def record_success(self) -> None:
        self._state = "closed"
        self._failures.clear()

    def record_failure(self) -> None:
        self._failures.append(time.monotonic())
        recent = sum(
            1 for t in self._failures
            if time.monotonic() - t <= self.recovery_timeout
        )
        if recent >= self.failure_threshold:
            self._state = "open"
            self._opened_at = time.monotonic()
            logger.error("Circuit breaker OPENED after %d failures", recent)

    async def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if self.is_open:
            raise RuntimeError(f"Circuit breaker is open — refusing call to {fn.__name__}")
        try:
            result = await fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise
