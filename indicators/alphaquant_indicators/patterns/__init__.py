"""Candlestick pattern detectors (causal, last completed bar)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PatternHit:
    name: str
    index: int
    bullish: bool | None


def _ohlc(o, h, l, c):
    return (
        np.asarray(o, dtype=float),
        np.asarray(h, dtype=float),
        np.asarray(l, dtype=float),
        np.asarray(c, dtype=float),
    )


def detect_engulfing(o, h, l, c) -> list[PatternHit]:
    o, h, l, c = _ohlc(o, h, l, c)
    hits: list[PatternHit] = []
    for i in range(1, len(c)):
        prev_bull = c[i - 1] > o[i - 1]
        curr_bull = c[i] > o[i]
        if not prev_bull and curr_bull and c[i] >= o[i - 1] and o[i] <= c[i - 1]:
            hits.append(PatternHit("bullish_engulfing", i, True))
        if prev_bull and not curr_bull and o[i] >= c[i - 1] and c[i] <= o[i - 1]:
            hits.append(PatternHit("bearish_engulfing", i, False))
    return hits


def detect_doji(o, h, l, c, *, body_frac: float = 0.1) -> list[PatternHit]:
    o, h, l, c = _ohlc(o, h, l, c)
    hits: list[PatternHit] = []
    for i in range(len(c)):
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        if abs(c[i] - o[i]) / rng <= body_frac:
            hits.append(PatternHit("doji", i, None))
    return hits


def detect_hammer(o, h, l, c) -> list[PatternHit]:
    o, h, l, c = _ohlc(o, h, l, c)
    hits: list[PatternHit] = []
    for i in range(len(c)):
        body = abs(c[i] - o[i])
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        lower = min(o[i], c[i]) - l[i]
        upper = h[i] - max(o[i], c[i])
        if lower >= 2 * body and upper <= body * 0.5:
            hits.append(PatternHit("hammer", i, True))
        if upper >= 2 * body and lower <= body * 0.5:
            hits.append(PatternHit("pin_bar_bearish", i, False))
    return hits


def detect_inside_outside(o, h, l, c) -> list[PatternHit]:
    o, h, l, c = _ohlc(o, h, l, c)
    hits: list[PatternHit] = []
    for i in range(1, len(c)):
        if h[i] <= h[i - 1] and l[i] >= l[i - 1]:
            hits.append(PatternHit("inside_bar", i, None))
        if h[i] >= h[i - 1] and l[i] <= l[i - 1]:
            hits.append(PatternHit("outside_bar", i, c[i] > o[i]))
    return hits


def detect_all_patterns(o, h, l, c) -> list[PatternHit]:
    return (
        detect_engulfing(o, h, l, c)
        + detect_doji(o, h, l, c)
        + detect_hammer(o, h, l, c)
        + detect_inside_outside(o, h, l, c)
    )
