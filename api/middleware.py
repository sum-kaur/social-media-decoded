"""FastAPI middleware — request ID injection and basic request logging."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attaches a unique X-Request-ID to every request and logs method/path/status/latency."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.monotonic()
        response: Response = await call_next(request)
        latency_ms = (time.monotonic() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s %d %.1fms req_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            request_id,
        )
        return response
