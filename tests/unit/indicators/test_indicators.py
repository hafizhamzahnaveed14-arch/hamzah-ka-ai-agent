"""Indicator and structure smoke tests."""

from __future__ import annotations

import numpy as np

from alphaquant_indicators.smc.fvg import GapSide, detect_fair_value_gaps
from alphaquant_indicators.structure.swings import (
    MarketBias,
    detect_swing_points,
    structure_bias,
)
from alphaquant_indicators.ta.core import ema, rsi, sma


def test_sma_ema_rsi_causal_length():
    closes = list(range(1, 51))
    s = sma(closes, 10)
    e = ema(closes, 10)
    r = rsi(closes, 14)
    assert len(s) == 50
    assert s.isna().sum() == 9
    assert e.notna().sum() > 0
    assert r.iloc[-1] > 50  # rising series


def test_swing_detection_on_synthetic_wave():
    # simple up-down wave
    x = np.linspace(0, 4 * np.pi, 80)
    close = 100 + 5 * np.sin(x)
    high = close + 0.5
    low = close - 0.5
    swings = detect_swing_points(high, low, left=2, right=2)
    assert len(swings) >= 4
    bias = structure_bias(swings)
    assert bias in {MarketBias.BULLISH, MarketBias.BEARISH, MarketBias.RANGE}


def test_bullish_fvg_detection():
    # Construct clear bullish FVG: candle0 high=10, candle2 low=12
    high = [10, 11, 13, 13]
    low = [9, 10, 12, 11.5]
    gaps = detect_fair_value_gaps(high, low)
    assert any(g.side == GapSide.BULLISH for g in gaps)
