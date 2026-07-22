"""Dev helper: 200x + 0.5% wallet sample (tight stop required)."""

from __future__ import annotations

from alphaquant_indicators.structure.swings import MarketBias
from alphaquant_risk.liquidation import max_stop_distance_before_liquidation
from alphaquant_shared.logging import configure_logging
from alphaquant_shared.types import ConfluenceItem, Side, Timeframe
from alphaquant_strategies.confluence.engine import (
    ConfluenceEngine,
    ConfluenceInput,
    TimeframeSnapshot,
)


def main() -> None:
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    configure_logging("INFO")

    entry = 3625.0
    # At 200x, stop MUST be tighter than liquidation distance
    max_dist = max_stop_distance_before_liquidation(entry=entry, leverage=200)
    stop = entry - max_dist * 0.7

    engine = ConfluenceEngine()
    idea = engine.evaluate(
        ConfluenceInput(
            symbol="ETHUSDT",
            entry=entry,
            stop_loss=stop,
            side=Side.LONG,
            account_equity=10_000,
            timeframe_snapshots=[
                TimeframeSnapshot(Timeframe.D1, MarketBias.BULLISH),
                TimeframeSnapshot(Timeframe.H4, MarketBias.BULLISH),
                TimeframeSnapshot(Timeframe.H1, MarketBias.BULLISH),
                TimeframeSnapshot(Timeframe.M15, MarketBias.BULLISH),
                TimeframeSnapshot(Timeframe.M5, MarketBias.BULLISH),
            ],
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
                ConfluenceItem(code="news", label="No high-impact news in next 2h", bullish=True),
            ],
        )
    )
    print(engine.format(idea))
    print(
        "\n(Rule: 200x + ≤0.5% wallet isolated margin. "
        "Wide stops => NO TRADE so liquidation is not hit. "
        "Confidence ≠ guaranteed profit.)"
    )


if __name__ == "__main__":
    main()
