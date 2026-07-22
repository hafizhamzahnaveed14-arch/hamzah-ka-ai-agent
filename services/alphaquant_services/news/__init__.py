"""News blackout filter service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class NewsEvent:
    name: str
    impact: str  # high | medium | low
    scheduled_at: datetime


@dataclass(frozen=True)
class BlackoutStatus:
    active: bool
    reason: str | None = None
    event: NewsEvent | None = None


class NewsFilter:
    """Blocks new entries around high-impact scheduled events."""

    HIGH_IMPACT_KEYWORDS = ("CPI", "FOMC", "NFP", "INTEREST RATE", "NONFARM")

    def __init__(self, buffer_minutes: int = 30) -> None:
        self.buffer = timedelta(minutes=buffer_minutes)

    def status(
        self,
        events: list[NewsEvent],
        *,
        now: datetime | None = None,
    ) -> BlackoutStatus:
        now = now or datetime.now(timezone.utc)
        for event in events:
            if event.impact.lower() != "high":
                continue
            start = event.scheduled_at - self.buffer
            end = event.scheduled_at + self.buffer
            if start <= now <= end:
                return BlackoutStatus(
                    active=True,
                    reason=f"{event.name} within blackout window (±{int(self.buffer.total_seconds() // 60)}m)",
                    event=event,
                )
        return BlackoutStatus(active=False)
