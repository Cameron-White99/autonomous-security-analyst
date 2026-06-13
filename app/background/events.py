"""In-process pub/sub for agent activity events, consumed by the SSE endpoint.

Each job keeps a history buffer so SSE clients that connect after analysis
started (or finished) still receive the full event sequence.
"""

import asyncio
from collections.abc import AsyncIterator

TERMINAL_EVENTS = {"complete", "error"}


class EventBus:
    def __init__(self) -> None:
        self._history: dict[str, list[dict]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._done: set[str] = set()

    def register_job(self, job_id: str) -> None:
        self._history.setdefault(job_id, [])

    def knows(self, job_id: str) -> bool:
        return job_id in self._history

    async def publish(self, job_id: str, event: dict) -> None:
        self._history.setdefault(job_id, []).append(event)
        if event.get("event") in TERMINAL_EVENTS:
            self._done.add(job_id)
        for queue in self._subscribers.get(job_id, []):
            await queue.put(event)

    async def subscribe(self, job_id: str) -> AsyncIterator[dict]:
        """Yield history first, then live events until a terminal event arrives."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(job_id, []).append(queue)
        try:
            history = list(self._history.get(job_id, []))
            for event in history:
                yield event
                if event.get("event") in TERMINAL_EVENTS:
                    return
            if job_id in self._done:
                return
            while True:
                event = await queue.get()
                yield event
                if event.get("event") in TERMINAL_EVENTS:
                    return
        finally:
            self._subscribers.get(job_id, []).remove(queue)


bus = EventBus()
