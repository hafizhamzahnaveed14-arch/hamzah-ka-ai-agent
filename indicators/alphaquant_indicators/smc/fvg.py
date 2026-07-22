"""Smart Money Concepts: Fair Value Gaps."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class GapSide(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True)
class FairValueGap:
    index: int  # middle candle index
    low: float
    high: float
    side: GapSide
    mitigated: bool = False


def detect_fair_value_gaps(
    high: pd.Series | np.ndarray | list[float],
    low: pd.Series | np.ndarray | list[float],
    *,
    min_gap_pct: float = 0.0,
) -> list[FairValueGap]:
    """3-candle FVG: candle[i-2].high < candle[i].low (bullish) or inverse."""
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    gaps: list[FairValueGap] = []
    for i in range(2, len(h)):
        # Bullish FVG
        if l[i] > h[i - 2]:
            gap_low, gap_high = float(h[i - 2]), float(l[i])
            mid = (gap_low + gap_high) / 2.0
            if mid > 0 and (gap_high - gap_low) / mid >= min_gap_pct:
                mitigated = any(l[j] <= gap_high and h[j] >= gap_low for j in range(i + 1, len(h)))
                gaps.append(
                    FairValueGap(
                        index=i - 1,
                        low=gap_low,
                        high=gap_high,
                        side=GapSide.BULLISH,
                        mitigated=mitigated,
                    )
                )
        # Bearish FVG
        if h[i] < l[i - 2]:
            gap_low, gap_high = float(h[i]), float(l[i - 2])
            mid = (gap_low + gap_high) / 2.0
            if mid > 0 and (gap_high - gap_low) / mid >= min_gap_pct:
                mitigated = any(l[j] <= gap_high and h[j] >= gap_low for j in range(i + 1, len(h)))
                gaps.append(
                    FairValueGap(
                        index=i - 1,
                        low=gap_low,
                        high=gap_high,
                        side=GapSide.BEARISH,
                        mitigated=mitigated,
                    )
                )
    return gaps
