from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        limit: int,
        window_seconds: int,
        auth_limit: int | None = None,
        auth_window_seconds: int | None = None,
        auth_path_prefix: str = "/auth",
    ) -> None:
        super().__init__(app)
        self.limit = max(limit, 1)
        self.window_seconds = max(window_seconds, 1)
        self.auth_limit = max(auth_limit or limit, 1)
        self.auth_window_seconds = max(auth_window_seconds or window_seconds, 1)
        self.auth_path_prefix = auth_path_prefix.rstrip("/")
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    @staticmethod
    def _client_key(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "").strip()
        if forwarded_for:
            first_ip = forwarded_for.split(",")[0].strip()
            if first_ip:
                return first_ip
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        now = monotonic()
        is_auth_request = request.url.path.startswith(self.auth_path_prefix)
        limit = self.auth_limit if is_auth_request else self.limit
        window_seconds = self.auth_window_seconds if is_auth_request else self.window_seconds
        client_key = f"{'auth' if is_auth_request else 'all'}:{self._client_key(request)}"

        async with self._lock:
            timestamps = self._requests[client_key]
            window_start = now - window_seconds
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= limit:
                retry_after = max(1, int(window_seconds - (now - timestamps[0])))
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                )
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(retry_after)
                return response

            timestamps.append(now)
            remaining = max(limit - len(timestamps), 0)
            reset_in = window_seconds if not timestamps else max(1, int(window_seconds - (now - timestamps[0])))

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_in)
        return response
