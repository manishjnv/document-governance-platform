"""Response-time monitoring middleware. T-3008."""

import time

from starlette.middleware.base import BaseHTTPMiddleware


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """Adds X-Response-Time-Ms header measured via perf_counter."""

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response
