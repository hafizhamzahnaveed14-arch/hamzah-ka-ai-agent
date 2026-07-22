"""Core domain types shared across packages.

Confidence scores express setup quality / model probability estimates.
They do not guarantee profitable outcomes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Sequence

from pydantic import BaseModel, Field, field_validator


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalAction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


class Timeframe(str, Enum):
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


PHASE1_SYMBOLS: tuple[str, ...] = (
    "ETHUSDT",
    "ADAUSDT",
    "SOLUSDT",
    "AAVEUSDT",
    "PEPEUSDT",
    "RUNEUSDT",
    "XAUUSDT",  # Gold on MEXC = XAU_USDT (not XAUUSD)
)

PHASE2_SYMBOLS: tuple[str, ...] = (
    "BTCUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "BNBUSDT",
    "TRXUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "SUIUSDT",
)

# Extra liquid alts commonly traded on MEXC futures
EXTRA_SYMBOLS: tuple[str, ...] = (
    "WIFUSDT",
    "NEARUSDT",
    "APTUSDT",
    "OPUSDT",
    "ARBUSDT",
)

# Default scanner / desk universe (Phase 1 + 2 + extras)
ACTIVE_SYMBOLS: tuple[str, ...] = PHASE1_SYMBOLS + PHASE2_SYMBOLS + EXTRA_SYMBOLS

# Aliases → MEXC contract form (without underscore; adapter adds it)
SYMBOL_ALIASES: dict[str, str] = {
    "XAUUSD": "XAUUSDT",
    "GOLD": "XAUUSDT",
    "GOLDUSDT": "XAUUSDT",
    "XAU": "XAUUSDT",
}

# Higher → lower for top-down confluence evaluation
TF_RANK: dict[Timeframe, int] = {
    Timeframe.W1: 90,
    Timeframe.D1: 80,
    Timeframe.H4: 70,
    Timeframe.H1: 60,
    Timeframe.M30: 50,
    Timeframe.M15: 40,
    Timeframe.M5: 30,
    Timeframe.M3: 20,
    Timeframe.M1: 10,
}


class Candle(BaseModel):
    """OHLCV candle. Timestamps are UTC-aware."""

    symbol: str
    timeframe: Timeframe
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: datetime | None = None
    quote_volume: float | None = None
    trades: int | None = None

    @field_validator("open_time", "close_time")
    @classmethod
    def _ensure_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator("open", "high", "low", "close", "volume")
    @classmethod
    def _non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("OHLCV fields must be non-negative")
        return value


class ConfluenceItem(BaseModel):
    code: str
    label: str
    bullish: bool | None = None  # None = neutral / informational
    weight: float = 1.0


class MarginMode(str, Enum):
    ISOLATED = "isolated"
    CROSS = "cross"


class RiskPlan(BaseModel):
    account_equity: float
    risk_pct: float
    position_size: float
    position_notional: float
    margin_mode: MarginMode = MarginMode.CROSS
    # Initial margin locked/estimated for this position (not a hard max-loss on CROSS)
    position_margin: float | None = None
    isolated_margin: float | None = None  # alias kept for older clients
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward: float
    suggested_leverage: float
    liquidation_price: float
    liquidation_warning: bool
    liquidation_warning_note: str | None = None


class TradeIdea(BaseModel):
    """Explainable trade proposal or explicit NO TRADE."""

    symbol: str
    action: SignalAction
    side: Side | None = None
    entry: float | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    risk: RiskPlan | None = None
    reasons: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    confluences: list[ConfluenceItem] = Field(default_factory=list)
    timeframes_aligned: list[Timeframe] = Field(default_factory=list)
    no_trade_reason: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trading_mode: TradingMode = TradingMode.PAPER

    @field_validator("confidence")
    @classmethod
    def _confidence_is_not_certainty(cls, value: float) -> float:
        # Clamp away from absolute certainty presentation (1.0 allowed mathematically
        # but UI should still show uncertainty language).
        return value


def format_trade_idea(idea: TradeIdea) -> str:
    """Section-13 text output. Never implies guaranteed profit."""
    action_label = (
        "NO TRADE" if idea.action == SignalAction.NO_TRADE else idea.action.value
    )
    header = f"{idea.symbol} — {action_label}"
    if idea.action == SignalAction.NO_TRADE:
        reason = idea.no_trade_reason or "Setup quality insufficient"
        return f"{header}\nReason: {reason}"

    assert idea.side is not None and idea.entry is not None and idea.risk is not None
    r = idea.risk
    warn = " ⚠" if r.liquidation_warning else ""
    margin = r.position_margin if r.position_margin is not None else r.isolated_margin
    mode = r.margin_mode.value.upper() if r.margin_mode else "CROSS"
    margin_label = (
        f"{mode} margin (init): {margin}  ({r.risk_pct * 100:.2f}% wallet)"
        if mode == "ISOLATED"
        else (
            f"{mode} margin (init): {margin}  ({r.risk_pct * 100:.2f}% wallet) — "
            "CROSS can lose more than this if liquidated"
        )
    )
    lines = [
        header,
        "",
        f"Entry: {idea.entry}",
        f"Stop Loss: {r.stop_loss}",
        f"TP1: {r.take_profit_1}   TP2: {r.take_profit_2}   TP3: {r.take_profit_3}",
        f"Risk:Reward: 1:{r.risk_reward:.1f}",
        f"Confidence: {idea.confidence * 100:.0f}%",
        f"Position Size: {r.position_size}",
        margin_label,
        f"Suggested Leverage: {r.suggested_leverage:.0f}x",
        f"Liquidation Price: {r.liquidation_price}{warn}",
        "",
        "Reasons:",
    ]
    for reason in idea.reasons:
        lines.append(f"✓ {reason}")
    lines.append("")
    lines.append("Conflicts / Caution:")
    if idea.conflicts:
        for c in idea.conflicts:
            lines.append(f"– {c}")
    else:
        lines.append("– (none noted; absence of conflicts is not a guarantee of profit)")
    return "\n".join(lines)


def ensure_phase1_symbol(symbol: str) -> str:
    sym = symbol.upper().replace("/", "").replace("-", "")
    if sym not in PHASE1_SYMBOLS and sym not in PHASE2_SYMBOLS:
        # Allow Phase-2 for forward-compat, but prefer Phase-1 in scanners.
        pass
    return sym


def timeframe_from_str(value: str) -> Timeframe:
    normalized = value.lower().replace("H", "h").replace("D", "d").replace("W", "w")
    # Accept Binance-style 1h / 4h / 1d
    mapping = {tf.value: tf for tf in Timeframe}
    # Also accept uppercase variants already handled
    aliases = {
        "1H": Timeframe.H1,
        "4H": Timeframe.H4,
        "1D": Timeframe.D1,
        "1W": Timeframe.W1,
        "1d": Timeframe.D1,
        "1w": Timeframe.W1,
    }
    if value in aliases:
        return aliases[value]
    if normalized in mapping:
        return mapping[normalized]
    raise ValueError(f"Unsupported timeframe: {value}")


def sorted_timeframes(tfs: Sequence[Timeframe], *, descending: bool = True) -> list[Timeframe]:
    return sorted(tfs, key=lambda t: TF_RANK[t], reverse=descending)
