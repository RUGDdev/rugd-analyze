"""Attempt limits for sign-in and registration. The rest of the app is not limited."""

from __future__ import annotations

import time
from typing import Callable

AUTH_LIMIT = 8
AUTH_WINDOW_SECONDS = 15 * 60
AUTH_LIMIT_MESSAGE = (
    "Too many sign-in or registration attempts from this network. "
    "Wait 15 minutes and try again. The rest of RUGD Analyze is still available."
)


class AttemptLimiter:
    """Sliding window of attempts for one key. A full window refuses another attempt."""

    def __init__(
        self,
        *,
        limit: int = AUTH_LIMIT,
        window_seconds: int = AUTH_WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = self._clock()
        recent = [
            stamp
            for stamp in self._hits.get(key, [])
            if now - stamp < self.window_seconds
        ]
        if len(recent) >= self.limit:
            self._hits[key] = recent
            return False
        recent.append(now)
        self._hits[key] = recent
        return True


def client_key(peer: str, forwarded: str | None) -> str:
    """Prefer the first forwarded address. Otherwise use the connection address."""
    first = (forwarded or "").split(",")[0].strip()
    if first:
        return first[:200]
    return (peer or "unknown")[:200]
