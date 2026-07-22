"""Confluence / NO TRADE hard-gate tests (200x-aware stops)."""

from __future__ import annotations

from alphaquant_indicators.structure.swings import MarketBias
from alphaquant_risk.liquidation import max_stop_distance_before_liquidation
from alphaquant_shared.types import ConfluenceItem, Side, SignalAction, Timeframe
from alphaquant_strategies.confluence.engine import (
    ConfluenceEngine,
    ConfluenceInput,
    TimeframeSnapshot,
)


def _aligned_snapshots() -> list[TimeframeSnapshot]:
    return [
        TimeframeSnapshot(Timeframe.D1, MarketBias.BULLISH),
        TimeframeSnapshot(Timeframe.H4, MarketBias.BULLISH),
        TimeframeSnapshot(Timeframe.H1, MarketBias.BULLISH),
        TimeframeSnapshot(Timeframe.M15, MarketBias.BULLISH),
    ]


def _tight_long_stop(entry: float = 3600.0) -> float:
    max_dist = max_stop_distance_before_liquidation(entry=entry, leverage=200)
    return entry - max_dist * 0.7


def test_news_blackout_forces_no_trade():
    engine = ConfluenceEngine()
    entry = 3600.0
    idea = engine.evaluate(
        ConfluenceInput(
            symbol="ETHUSDT",
            entry=entry,
            stop_loss=_tight_long_stop(entry),
            side=Side.LONG,
            timeframe_snapshots=_aligned_snapshots(),
            confluences=[
                ConfluenceItem(code="bos", label="Break of Structure", bullish=True)
            ]
            * 5,
            news_blackout=True,
            news_reason="CPI in 20 minutes",
        )
    )
    assert idea.action == SignalAction.NO_TRADE
    assert "CPI" in (idea.no_trade_reason or "")


def test_insufficient_tf_alignment_no_trade():
    engine = ConfluenceEngine()
    entry = 3600.0
    idea = engine.evaluate(
        ConfluenceInput(
            symbol="ETHUSDT",
            entry=entry,
            stop_loss=_tight_long_stop(entry),
            side=Side.LONG,
            timeframe_snapshots=[
                TimeframeSnapshot(Timeframe.D1, MarketBias.BULLISH),
                TimeframeSnapshot(Timeframe.H4, MarketBias.BEARISH),
                TimeframeSnapshot(Timeframe.H1, MarketBias.RANGE),
            ],
            confluences=[ConfluenceItem(code="x", label="x", bullish=True)] * 8,
        )
    )
    assert idea.action == SignalAction.NO_TRADE
    assert "timeframe" in (idea.no_trade_reason or "").lower()


def test_low_confidence_no_trade():
    engine = ConfluenceEngine()
    entry = 150.0
    idea = engine.evaluate(
        ConfluenceInput(
            symbol="SOLUSDT",
            entry=entry,
            stop_loss=_tight_long_stop(entry),
            side=Side.LONG,
            timeframe_snapshots=_aligned_snapshots(),
            confluences=[],
            conflicts=["Multiple opposing signals"],
        )
    )
    assert idea.action == SignalAction.NO_TRADE
    assert "Confidence" in (idea.no_trade_reason or "")


def test_wide_stop_at_200x_becomes_no_trade():
    engine = ConfluenceEngine()
    idea = engine.evaluate(
        ConfluenceInput(
            symbol="ETHUSDT",
            entry=3600,
            stop_loss=3550,
            side=Side.LONG,
            timeframe_snapshots=_aligned_snapshots(),
            confluences=[
                ConfluenceItem(code="bos", label="Break of Structure (BOS)", bullish=True),
                ConfluenceItem(code="ob", label="Bullish Order Block reaction", bullish=True),
                ConfluenceItem(code="fvg", label="FVG filled", bullish=True),
                ConfluenceItem(code="rsi", label="RSI recovering from oversold", bullish=True),
                ConfluenceItem(
                    code="ema", label="EMA alignment (Daily/4H/1H bullish)", bullish=True
                ),
                ConfluenceItem(
                    code="vol", label="Above-average volume on trigger candle", bullish=True
                ),
            ],
        )
    )
    assert idea.action == SignalAction.NO_TRADE
    assert "200" in (idea.no_trade_reason or "") or "liquidation" in (
        idea.no_trade_reason or ""
    ).lower() or "stop" in (idea.no_trade_reason or "").lower()


def test_valid_setup_200x_tight_stop():
    engine = ConfluenceEngine()
    entry = 3600.0
    stop = _tight_long_stop(entry)
    idea = engine.evaluate(
        ConfluenceInput(
            symbol="ETHUSDT",
            entry=entry,
            stop_loss=stop,
            side=Side.LONG,
            timeframe_snapshots=_aligned_snapshots(),
            confluences=[
                ConfluenceItem(code="bos", label="Break of Structure (BOS)", bullish=True),
                ConfluenceItem(code="ob", label="Bullish Order Block reaction", bullish=True),
                ConfluenceItem(code="fvg", label="FVG filled", bullish=True),
                ConfluenceItem(code="rsi", label="RSI recovering from oversold", bullish=True),
                ConfluenceItem(
                    code="ema", label="EMA alignment (Daily/4H/1H bullish)", bullish=True
                ),
                ConfluenceItem(
                    code="vol", label="Above-average volume on trigger candle", bullish=True
                ),
            ],
        )
    )
    assert idea.action == SignalAction.LONG
    assert idea.confidence >= 0.85
    assert idea.risk is not None
    assert idea.risk.suggested_leverage == 200
    assert idea.risk.risk_pct <= 0.005
    assert idea.risk.liquidation_price < stop
    text = engine.format(idea)
    assert "ETHUSDT — LONG" in text
    assert "200x" in text or "200" in text
