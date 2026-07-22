"""News filter tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from alphaquant_services.news import NewsEvent, NewsFilter


def test_blackout_around_cpi():
    now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
    events = [
        NewsEvent("US CPI", "high", now + timedelta(minutes=10)),
    ]
    status = NewsFilter(buffer_minutes=30).status(events, now=now)
    assert status.active
    assert status.reason is not None


def test_no_blackout_outside_window():
    now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
    events = [
        NewsEvent("US CPI", "high", now + timedelta(hours=5)),
    ]
    status = NewsFilter(buffer_minutes=30).status(events, now=now)
    assert not status.active
