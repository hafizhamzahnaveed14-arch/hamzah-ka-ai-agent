"""Signal evaluation routes — human-in-the-loop proposals only."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from alphaquant_indicators.structure.swings import MarketBias
from alphaquant_shared.types import ConfluenceItem, Side, TradingMode, timeframe_from_str
from alphaquant_strategies.confluence.engine import (
    ConfluenceEngine,
    ConfluenceInput,
    TimeframeSnapshot,
)

router = APIRouter()


class TimeframeBiasIn(BaseModel):
    timeframe: str
    bias: str  # bullish | bearish | range


class EvaluateSignalRequest(BaseModel):
    symbol: str
    side: Side
    entry: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    account_equity: float = Field(default=10_000, gt=0)
    risk_pct: float | None = Field(default=None, gt=0, le=0.005)
    timeframes: list[TimeframeBiasIn]
    confluence_labels: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    news_blackout: bool = False
    news_reason: str | None = None


@router.post("/signals/evaluate")
async def evaluate_signal(body: EvaluateSignalRequest):
    """Rule-based confluence evaluation. Returns LONG/SHORT/NO_TRADE with reasons."""
    snapshots: list[TimeframeSnapshot] = []
    try:
        for tf in body.timeframes:
            snapshots.append(
                TimeframeSnapshot(
                    timeframe=timeframe_from_str(tf.timeframe),
                    bias=MarketBias(tf.bias.lower()),
                )
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    confluences = [
        ConfluenceItem(code=f"c{i}", label=label, bullish=True)
        for i, label in enumerate(body.confluence_labels)
    ]
    engine = ConfluenceEngine(trading_mode=TradingMode.PAPER)
    idea = engine.evaluate(
        ConfluenceInput(
            symbol=body.symbol,
            entry=body.entry,
            stop_loss=body.stop_loss,
            side=body.side,
            timeframe_snapshots=snapshots,
            confluences=confluences,
            conflicts=list(body.conflicts),
            news_blackout=body.news_blackout,
            news_reason=body.news_reason,
            account_equity=body.account_equity,
            risk_pct=body.risk_pct,
        )
    )
    return {
        "idea": idea.model_dump(mode="json"),
        "formatted": engine.format(idea),
        "disclaimer": (
            "Confidence reflects setup quality, not a guarantee of profit. "
            "Human confirmation required before any execution."
        ),
    }
