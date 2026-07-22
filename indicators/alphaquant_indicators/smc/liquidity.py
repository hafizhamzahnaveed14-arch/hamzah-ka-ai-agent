"""Additional SMC helpers: liquidity, equal highs/lows, premium/discount."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from alphaquant_indicators.structure.swings import SwingPoint, SwingType


@dataclass(frozen=True)
class EqualLevel:
    kind: str  # "EQH" or "EQL"
    price: float
    indices: tuple[int, int]


@dataclass(frozen=True)
class LiquidityPool:
    price: float
    kind: str  # "buy_side" (above highs) or "sell_side" (below lows)
    swing_index: int


def detect_equal_highs_lows(
    swings: list[SwingPoint],
    *,
    tolerance_pct: float = 0.001,
) -> list[EqualLevel]:
    equals: list[EqualLevel] = []
    highs = [s for s in swings if s.kind == SwingType.HIGH]
    lows = [s for s in swings if s.kind == SwingType.LOW]
    for a, b in zip(highs, highs[1:]):
        mid = (a.price + b.price) / 2.0
        if mid > 0 and abs(a.price - b.price) / mid <= tolerance_pct:
            equals.append(EqualLevel("EQH", mid, (a.index, b.index)))
    for a, b in zip(lows, lows[1:]):
        mid = (a.price + b.price) / 2.0
        if mid > 0 and abs(a.price - b.price) / mid <= tolerance_pct:
            equals.append(EqualLevel("EQL", mid, (a.index, b.index)))
    return equals


def detect_liquidity_pools(swings: list[SwingPoint]) -> list[LiquidityPool]:
    pools: list[LiquidityPool] = []
    for s in swings:
        if s.kind == SwingType.HIGH:
            pools.append(LiquidityPool(price=s.price, kind="buy_side", swing_index=s.index))
        else:
            pools.append(LiquidityPool(price=s.price, kind="sell_side", swing_index=s.index))
    return pools


def premium_discount_zone(
    swing_low: float,
    swing_high: float,
    price: float,
) -> str:
    """Return 'premium', 'discount', or 'equilibrium' vs dealing range."""
    if swing_high <= swing_low:
        return "equilibrium"
    mid = (swing_high + swing_low) / 2.0
    if price > mid:
        return "premium"
    if price < mid:
        return "discount"
    return "equilibrium"
