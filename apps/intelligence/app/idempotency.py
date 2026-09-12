"""
Idempotency.

Laravel retries. Queues retry. Operators retry. Without a key, each retry buys
another ASR call and produces a second transcript of identical audio — expensive,
and worse, it lets two different transcripts of the same recording exist.

The key is supplied by Laravel (`Idempotency-Key`) because Laravel is the one
that knows a retry is a retry. In-process TTL cache: this service is stateless by
design, so the cache is a cost optimisation and a consistency aid within a
worker's lifetime, not a durability guarantee. The durable idempotency record
lives in Postgres on the Laravel side (`transcript_runs.idempotency_key`).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

DEFAULT_TTL_SECONDS = 900
MAX_ENTRIES = 512


class IdempotencyCache:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.ttl = ttl_seconds
        self._entries: dict[str, tuple[float, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def run(self, key: str | None, factory: Callable[[], Awaitable[Any]]) -> Any:
        if not key:
            return await factory()

        cached = self._get(key)
        if cached is not None:
            return cached

        # Per-key lock: two concurrent retries of the same request must produce
        # one upstream call, not two.
        async with self._guard:
            lock = self._locks.setdefault(key, asyncio.Lock())

        async with lock:
            cached = self._get(key)
            if cached is not None:
                return cached

            result = await factory()
            self._put(key, result)
            return result

    def _get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None

        expires_at, value = entry
        if expires_at < time.monotonic():
            self._entries.pop(key, None)
            return None

        return value

    def _put(self, key: str, value: Any) -> None:
        if len(self._entries) >= MAX_ENTRIES:
            oldest = min(self._entries, key=lambda k: self._entries[k][0])
            self._entries.pop(oldest, None)
            self._locks.pop(oldest, None)

        self._entries[key] = (time.monotonic() + self.ttl, value)


transcription_cache = IdempotencyCache()
