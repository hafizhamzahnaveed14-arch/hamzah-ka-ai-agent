"""Smart Money Concepts: Order Blocks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class OrderBlockSide(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True)
class OrderBlock:
    index: int
    low: float
    high: float
    side: OrderBlockSide
    mitigated: bool = False


def detect_order_blocks(
    open_: pd.Series | np.ndarray | list[float],
    high: pd.Series | np.ndarray | list[float],
    low: pd.Series | np.ndarray | list[float],
    close: pd.Series | np.ndarray | list[float],
    *,
    impulse_factor: float = 1.5,
) -> list[OrderBlock]:
    """Heuristic OB: last opposing candle before an impulsive displacement.

    Bullish OB = last down-close candle before a strong up move.
    Bearish OB = last up-close candle before a strong down move.
    """
    o = np.asarray(open_, dtype=float)
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    c = np.asarray(close, dtype=float)
    ranges = h - l
    avg_range = pd.Series(ranges).rolling(20, min_periods=5).mean().to_numpy()

    blocks: list[OrderBlock] = []
    for i in range(1, len(c) - 1):
        if np.isnan(avg_range[i]) or avg_range[i] <= 0:
            continue
        body = abs(c[i] - o[i])
        # Impulsive bullish candle
        if c[i] > o[i] and ranges[i] >= impulse_factor * avg_range[i]:
            # look back for last bearish candle
            for j in range(i - 1, max(-1, i - 6), -1):
                if c[j] < o[j]:
                    mitigated = any(l[k] <= h[j] and h[k] >= l[j] for k in range(i + 1, len(c)))
                    blocks.append(
                        OrderBlock(
                            index=j,
                            low=float(l[j]),
                            high=float(h[j]),
                            side=OrderBlockSide.BULLISH,
                            mitigated=mitigated,
                        )
                    )
                    break
        # Impulsive bearish candle
        if c[i] < o[i] and ranges[i] >= impulse_factor * avg_range[i]:
            for j in range(i - 1, max(-1, i - 6), -1):
                if c[j] > o[j]:
                    mitigated = any(l[k] <= h[j] and h[k] >= l[j] for k in range(i + 1, len(c)))
                    blocks.append(
                        OrderBlock(
                            index=j,
                            low=float(l[j]),
                            high=float(h[j]),
                            side=OrderBlockSide.BEARISH,
                            mitigated=mitigated,
                        )
                    )
                    break
    return blocks
