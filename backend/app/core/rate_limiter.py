"""A small in-memory limiter: at most N requests per key within a time window.

Counts live in this process's memory, so they reset when the server restarts and are not
shared between several server processes. That is fine for a prototype; a production
system would keep the counts in a shared store such as Redis.
"""

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock


class SlidingWindowRateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def try_acquire(self, key: str) -> int | None:
        """Record a request. Return None if allowed, else the seconds to wait before retrying."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self._window_seconds:
                hits.popleft()
            if len(hits) >= self._max_requests:
                return math.ceil(self._window_seconds - (now - hits[0]))
            hits.append(now)
            return None
