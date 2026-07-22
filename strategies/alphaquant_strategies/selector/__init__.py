"""Simple regime-based strategy selector stub."""

from __future__ import annotations

from enum import Enum

from alphaquant_indicators.structure.swings import MarketBias


class StrategyKind(str, Enum):
    TREND_PULLBACK = "trend_pullback"
    RANGE_REVERSION = "range_reversion"
    BREAKOUT = "breakout"
    NO_SETUP = "no_setup"


def select_strategy(bias: MarketBias, *, adx_value: float | None = None) -> StrategyKind:
    """Pick a confluence playbook for the current regime.

    Returns NO_SETUP often when regime is unclear — callers should prefer NO TRADE.
    """
    if bias == MarketBias.RANGE:
        if adx_value is not None and adx_value < 18:
            return StrategyKind.RANGE_REVERSION
        return StrategyKind.NO_SETUP
    if adx_value is not None and adx_value >= 25:
        return StrategyKind.TREND_PULLBACK
    if adx_value is not None and adx_value >= 20:
        return StrategyKind.BREAKOUT
    return StrategyKind.NO_SETUP
