"""Market structure: swings, HH/HL/LH/LL, BOS, CHoCH, bias."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class SwingType(str, Enum):
    HIGH = "swing_high"
    LOW = "swing_low"


class StructureEventType(str, Enum):
    BOS = "bos"
    CHOCH = "choch"


class MarketBias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGE = "range"


@dataclass(frozen=True)
class SwingPoint:
    index: int
    price: float
    kind: SwingType


@dataclass(frozen=True)
class StructureEvent:
    index: int
    price: float
    event: StructureEventType
    direction: MarketBias
    broken_level: float


def detect_swing_points(
    high: pd.Series | np.ndarray | list[float],
    low: pd.Series | np.ndarray | list[float],
    *,
    left: int = 2,
    right: int = 2,
) -> list[SwingPoint]:
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    n = len(h)
    swings: list[SwingPoint] = []
    for i in range(left, n - right):
        window_h = h[i - left : i + right + 1]
        window_l = l[i - left : i + right + 1]
        if h[i] == np.max(window_h) and np.sum(window_h == h[i]) == 1:
            swings.append(SwingPoint(index=i, price=float(h[i]), kind=SwingType.HIGH))
        if l[i] == np.min(window_l) and np.sum(window_l == l[i]) == 1:
            swings.append(SwingPoint(index=i, price=float(l[i]), kind=SwingType.LOW))
    return swings


def classify_swing_structure(swings: list[SwingPoint]) -> list[str]:
    labels: list[str] = []
    last_high: SwingPoint | None = None
    last_low: SwingPoint | None = None
    for s in swings:
        if s.kind == SwingType.HIGH:
            labels.append("H" if last_high is None else ("HH" if s.price > last_high.price else "LH"))
            last_high = s
        else:
            labels.append("L" if last_low is None else ("HL" if s.price > last_low.price else "LL"))
            last_low = s
    return labels


def detect_bos_choch(
    closes: pd.Series | np.ndarray | list[float],
    swings: list[SwingPoint],
    *,
    bias: MarketBias = MarketBias.RANGE,
) -> list[StructureEvent]:
    c = np.asarray(closes, dtype=float)
    events: list[StructureEvent] = []
    last_high = None
    last_low = None
    current_bias = bias

    for s in swings:
        if s.kind == SwingType.HIGH:
            last_high = s
        else:
            last_low = s
        i = s.index
        for j in range(i + 1, min(len(c), i + 5)):
            price = float(c[j])
            if last_high and price > last_high.price:
                event_type = (
                    StructureEventType.BOS
                    if current_bias == MarketBias.BULLISH
                    else StructureEventType.CHOCH
                )
                events.append(
                    StructureEvent(
                        index=j,
                        price=price,
                        event=event_type,
                        direction=MarketBias.BULLISH,
                        broken_level=last_high.price,
                    )
                )
                current_bias = MarketBias.BULLISH
                break
            if last_low and price < last_low.price:
                event_type = (
                    StructureEventType.BOS
                    if current_bias == MarketBias.BEARISH
                    else StructureEventType.CHOCH
                )
                events.append(
                    StructureEvent(
                        index=j,
                        price=price,
                        event=event_type,
                        direction=MarketBias.BEARISH,
                        broken_level=last_low.price,
                    )
                )
                current_bias = MarketBias.BEARISH
                break
    return events


def structure_bias(swings: list[SwingPoint]) -> MarketBias:
    labels = classify_swing_structure(swings)
    recent = labels[-6:]
    bull = sum(1 for x in recent if x in {"HH", "HL"})
    bear = sum(1 for x in recent if x in {"LH", "LL"})
    if bull >= bear + 2:
        return MarketBias.BULLISH
    if bear >= bull + 2:
        return MarketBias.BEARISH
    return MarketBias.RANGE
