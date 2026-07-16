"""
Minimal in-process rate limiter for sensitive endpoints (login, signup,
refresh, scan-trigger). Deliberately dependency-free.

Limitation (documented, not hidden): this state is per-process. If the
backend is horizontally scaled across multiple workers/containers without a
shared store, each process enforces its own limit independently, so the
effective global limit is (per-process limit x worker count). For a
single-process/single-container deployment (as shipped in this repo's
Dockerfile/render.yaml) this is a real, correct limit. For real multi-worker
production scaling, swap the in-memory dict below for a Redis-backed
sliding-window counter (e.g. via `redis` + `INCR`/`EXPIRE`) — the call sites
in app/api/*.py wouldn't need to change since they only see check().
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please slow down and try again shortly.",
                )
            hits.append(now)


def client_ip(request: Request) -> str:
    # Trust X-Forwarded-For only if you additionally configure your reverse
    # proxy to strip/overwrite client-supplied values for this header before
    # it reaches the app (Render/most PaaS do this correctly by default).
    # Falling back to request.client.host keeps this safe when unset.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
