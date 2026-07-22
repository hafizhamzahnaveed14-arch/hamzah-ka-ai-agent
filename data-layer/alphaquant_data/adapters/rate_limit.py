"""Simple token-bucket rate limiter for REST calls."""

from __future__ import annotations

import asyncio
import time

from alphaquant_shared.errors import RateLimitError


class RateLimiter:
    """Token bucket. Raises RateLimitError if wait would exceed max_wait_s."""

    def __init__(self, requests_per_minute: int, *, max_wait_s: float = 30.0) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self.capacity = float(requests_per_minute)
        self.tokens = float(requests_per_minute)
        self.refill_per_sec = requests_per_minute / 60.0
        self.max_wait_s = max_wait_s
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated_at
        self._updated_at = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return
            deficit = tokens - self.tokens
            wait_s = deficit / self.refill_per_sec
            if wait_s > self.max_wait_s:
                raise RateLimitError(
                    f"Rate limit would require waiting {wait_s:.1f}s (max {self.max_wait_s}s)"
                )
            await asyncio.sleep(wait_s)
            self._refill()
            self.tokens -= tokens
