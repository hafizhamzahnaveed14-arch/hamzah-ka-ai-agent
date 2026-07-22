"""Sentiment stubs — minor confirming factor only, never a primary trigger."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SentimentReading:
    fear_greed: int | None  # 0-100
    label: str
    note: str


def interpret_fear_greed(value: int | None) -> SentimentReading:
    if value is None:
        return SentimentReading(
            None,
            "unavailable",
            "Sentiment unavailable; do not block or force trades on missing data.",
        )
    if value <= 25:
        label = "extreme_fear"
    elif value <= 45:
        label = "fear"
    elif value <= 55:
        label = "neutral"
    elif value <= 75:
        label = "greed"
    else:
        label = "extreme_greed"
    return SentimentReading(
        value,
        label,
        "Sentiment is noisy — use only as a minor confluence, never as the primary trigger.",
    )
