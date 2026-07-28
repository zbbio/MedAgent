"""Generation admission control and in-memory service metrics."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from time import perf_counter
from typing import AsyncIterator


class QueueFullError(RuntimeError):
    pass


class QueueWaitTimeoutError(RuntimeError):
    pass


class GenerationGate:
    """Bound only expensive answer-generation chains, with a short bounded queue."""

    def __init__(self, max_active: int, max_pending: int, wait_seconds: float) -> None:
        self.max_active = max_active
        self.max_pending = max_pending
        self.wait_seconds = wait_seconds
        self.active = 0
        self.pending = 0
        self._condition = asyncio.Condition()

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[float]:
        queued_at = perf_counter()
        queued = False
        async with self._condition:
            if self.active >= self.max_active:
                if self.pending >= self.max_pending:
                    raise QueueFullError("生成队列已满")
                self.pending += 1
                queued = True
                try:
                    await asyncio.wait_for(
                        self._condition.wait_for(lambda: self.active < self.max_active),
                        timeout=self.wait_seconds,
                    )
                except asyncio.TimeoutError as exc:
                    raise QueueWaitTimeoutError("等待生成名额超时") from exc
                finally:
                    self.pending -= 1
            self.active += 1

        wait_ms = round((perf_counter() - queued_at) * 1000, 2) if queued else 0.0
        try:
            yield wait_ms
        finally:
            async with self._condition:
                self.active -= 1
                self._condition.notify(1)

    def snapshot(self) -> dict[str, int]:
        return {
            "active": self.active,
            "pending": self.pending,
            "max_active": self.max_active,
            "max_pending": self.max_pending,
        }


class ServiceMetrics:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._duration_total_ms = 0.0
        self._duration_samples = 0

    async def record(
        self,
        outcome: str,
        *,
        duration_ms: float | None = None,
        upstream_rate_limited: bool = False,
    ) -> None:
        async with self._lock:
            self._counters["requests"] += 1
            self._counters[outcome] += 1
            if upstream_rate_limited:
                self._counters["upstream_rate_limited"] += 1
            if duration_ms is not None:
                self._duration_total_ms += duration_ms
                self._duration_samples += 1

    async def snapshot(self) -> dict[str, int | float]:
        async with self._lock:
            average = (
                round(self._duration_total_ms / self._duration_samples, 2)
                if self._duration_samples
                else 0.0
            )
            return {
                "requests": self._counters["requests"],
                "success": self._counters["success"],
                "errors": self._counters["errors"],
                "http_429": self._counters["http_429"],
                "http_504": self._counters["http_504"],
                "upstream_rate_limited": self._counters["upstream_rate_limited"],
                "average_total_ms": average,
            }
