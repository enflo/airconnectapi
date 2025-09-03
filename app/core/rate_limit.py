import time
import threading
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple in-memory fixed-window rate limiter per client IP.

    This is a lightweight solution suitable for single-process deployments and tests.
    For multi-process or distributed deployments, use a shared store (Redis) instead.
    """

    def __init__(
        self,
        app,
        *,
        enabled: bool = True,
        limit: int = 120,
        window_seconds: int = 60,
        scope_prefix: str = "/api",
        header_client_ip: Optional[str] = None,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.limit = max(1, int(limit))
        self.window = max(1, int(window_seconds))
        self.scope_prefix = scope_prefix or "/api"
        self.header_client_ip = (header_client_ip or "").strip() or None
        # key: (ip, window_start) -> count
        self._counts: dict[tuple[str, int], int] = {}
        self._lock = threading.Lock()

    def _client_id(self, request: Request) -> str:
        # If a forwarding header is configured, trust first IP in list
        if self.header_client_ip:
            hdr = request.headers.get(self.header_client_ip)
            if hdr:
                return hdr.split(",")[0].strip() or "anonymous"
        client = request.client
        return (client.host if client else "anonymous") or "anonymous"

    def _now_window(self) -> int:
        now = int(time.time())
        return now - (now % self.window)

    def _inc(self, ip: str, window_start: int) -> int:
        key = (ip, window_start)
        with self._lock:
            # Clean old windows occasionally to avoid unbounded growth
            # Only when dict grows beyond a small threshold
            if len(self._counts) > 1024:
                to_del = [k for k in self._counts if k[1] < window_start]
                for k in to_del:
                    self._counts.pop(k, None)
            cnt = self._counts.get(key, 0) + 1
            self._counts[key] = cnt
            return cnt

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:  # type: ignore[override]
        if not self.enabled:
            return await call_next(request)

        # Scope only to matching path prefix
        path = request.url.path or ""
        if not path.startswith(self.scope_prefix):
            return await call_next(request)

        ip = self._client_id(request)
        window_start = self._now_window()
        count = self._inc(ip, window_start)
        remaining = max(0, self.limit - count)
        reset_in = self.window - (int(time.time()) - window_start)

        if count > self.limit:
            # Too many requests
            headers = {
                "X-RateLimit-Limit": str(self.limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(max(1, reset_in)),
            }
            return JSONResponse(
                {"detail": "Too Many Requests"}, status_code=429, headers=headers
            )

        # Proceed with request
        response = await call_next(request)
        try:
            # Attach headers for visibility
            response.headers["X-RateLimit-Limit"] = str(self.limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        except Exception:
            pass
        return response
