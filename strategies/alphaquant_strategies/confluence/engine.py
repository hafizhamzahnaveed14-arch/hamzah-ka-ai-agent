"""Confluence / decision logic — rule-based first (before ML).

Hard gates (no exceptions):
- Risk:Reward < 2 → NO TRADE
- Confidence < 85% → NO TRADE
- News blackout active → NO TRADE
- Timeframe conflict (insufficient alignment) → NO TRADE
"""

from __future__ import annotations

from dataclasses import dataclass, field

from alphaquant_indicators.structure.swings import MarketBias
from alphaquant_risk.engine import RiskEngine, RiskEngineConfig
from alphaquant_shared.config import get_settings
from alphaquant_shared.errors import RiskViolationError
from alphaquant_shared.types import (
    ConfluenceItem,
    Side,
    SignalAction,
    Timeframe,
    TradeIdea,
    TradingMode,
    format_trade_idea,
)


@dataclass
class TimeframeSnapshot:
    timeframe: Timeframe
    bias: MarketBias
    notes: list[str] = field(default_factory=list)


@dataclass
class ConfluenceInput:
    symbol: str
    entry: float
    stop_loss: float
    side: Side
    timeframe_snapshots: list[TimeframeSnapshot]
    confluences: list[ConfluenceItem] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    news_blackout: bool = False
    news_reason: str | None = None
    account_equity: float = 10_000.0
    risk_pct: float | None = None


@dataclass
class DecisionConfig:
    min_aligned_timeframes: int = 3
    min_confidence: float = 0.85
    min_risk_reward: float = 2.0
    base_confidence: float = 0.55
    confluence_weight: float = 0.06
    conflict_penalty: float = 0.08
    alignment_bonus: float = 0.05


class ConfluenceEngine:
    """Produces TradeIdea or NO TRADE with explicit reasons."""

    def __init__(
        self,
        risk_engine: RiskEngine | None = None,
        config: DecisionConfig | None = None,
        trading_mode: TradingMode = TradingMode.PAPER,
    ) -> None:
        settings = get_settings()
        self.risk = risk_engine or RiskEngine(
            RiskEngineConfig(
                risk_per_trade_pct=settings.risk_per_trade_pct,
                hard_cap_pct=settings.risk_per_trade_hard_cap_pct,
                max_concurrent_risk_pct=settings.max_concurrent_risk_pct,
                daily_loss_limit_pct=settings.daily_loss_limit_pct,
                min_risk_reward=settings.min_risk_reward,
                margin_mode=settings.margin_mode,
                max_leverage=settings.max_leverage,
                target_leverage=settings.target_leverage,
                use_fixed_leverage=settings.use_fixed_leverage,
                leverage_safety_buffer=settings.leverage_safety_buffer,
                stop_liq_buffer_fraction=settings.stop_liq_buffer_fraction,
                maintenance_margin_rate=settings.maintenance_margin_rate,
            )
        )
        self.config = config or DecisionConfig(
            min_confidence=settings.min_confidence,
            min_risk_reward=settings.min_risk_reward,
        )
        self.trading_mode = trading_mode

    def evaluate(self, data: ConfluenceInput) -> TradeIdea:
        # --- Hard gate: news ---
        if data.news_blackout:
            return self._no_trade(
                data.symbol,
                data.news_reason or "High-impact news blackout window active",
            )

        aligned, conflict_msgs = self._assess_timeframes(data.side, data.timeframe_snapshots)
        conflicts = list(data.conflicts) + conflict_msgs

        if len(aligned) < self.config.min_aligned_timeframes:
            return self._no_trade(
                data.symbol,
                f"Only {len(aligned)} timeframe(s) aligned; need "
                f"{self.config.min_aligned_timeframes}",
            )

        confidence = self._score_confidence(data.confluences, conflicts, len(aligned))
        if confidence < self.config.min_confidence:
            return self._no_trade(
                data.symbol,
                f"Confidence {confidence * 100:.0f}%, below "
                f"{self.config.min_confidence * 100:.0f}% threshold",
            )

        try:
            plan = self.risk.build_plan(
                side=data.side,
                entry=data.entry,
                stop_loss=data.stop_loss,
                account_equity=data.account_equity,
                risk_pct=data.risk_pct,
            )
        except RiskViolationError as exc:
            return self._no_trade(data.symbol, str(exc))

        if plan.risk_reward < self.config.min_risk_reward:
            return self._no_trade(
                data.symbol,
                f"Risk:Reward {plan.risk_reward:.2f} < {self.config.min_risk_reward}",
            )

        reasons = [c.label for c in data.confluences if c.bullish is not False]
        reasons.append(
            f"Multi-timeframe alignment: {', '.join(tf.value for tf in aligned)}"
        )
        if plan.liquidation_warning and plan.liquidation_warning_note:
            conflicts.append(plan.liquidation_warning_note)

        action = SignalAction.LONG if data.side == Side.LONG else SignalAction.SHORT
        return TradeIdea(
            symbol=data.symbol.upper(),
            action=action,
            side=data.side,
            entry=data.entry,
            confidence=round(confidence, 4),
            risk=plan,
            reasons=reasons,
            conflicts=conflicts,
            confluences=data.confluences,
            timeframes_aligned=aligned,
            trading_mode=self.trading_mode,
        )

    def format(self, idea: TradeIdea) -> str:
        return format_trade_idea(idea)

    def _no_trade(self, symbol: str, reason: str) -> TradeIdea:
        return TradeIdea(
            symbol=symbol.upper(),
            action=SignalAction.NO_TRADE,
            confidence=0.0,
            no_trade_reason=reason,
            conflicts=[],
            reasons=[],
            trading_mode=self.trading_mode,
        )

    def _assess_timeframes(
        self,
        side: Side,
        snapshots: list[TimeframeSnapshot],
    ) -> tuple[list[Timeframe], list[str]]:
        want = MarketBias.BULLISH if side == Side.LONG else MarketBias.BEARISH
        aligned: list[Timeframe] = []
        conflicts: list[str] = []
        for snap in snapshots:
            if snap.bias == want:
                aligned.append(snap.timeframe)
            elif snap.bias == MarketBias.RANGE:
                conflicts.append(
                    f"{snap.timeframe.value} is ranging (neither confirms nor strongly opposes)"
                )
            else:
                conflicts.append(
                    f"{snap.timeframe.value} bias is {snap.bias.value}, conflicts with {side.value}"
                )
        return aligned, conflicts

    def _score_confidence(
        self,
        confluences: list[ConfluenceItem],
        conflicts: list[str],
        aligned_count: int,
    ) -> float:
        score = self.config.base_confidence
        for item in confluences:
            w = item.weight * self.config.confluence_weight
            if item.bullish is True:
                score += w
            elif item.bullish is False:
                score -= w
            else:
                score += w * 0.25
        score += min(aligned_count, 5) * self.config.alignment_bonus
        score -= len(conflicts) * self.config.conflict_penalty
        return float(max(0.0, min(0.99, score)))  # never present as absolute certainty
