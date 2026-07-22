"""Live execution — human-confirm only. Autopilot stays OFF.

Hard gates still apply: risk ≤ 0.5%, stop before liq, RR ≥ 2, confidence ≥ 85%.
Requires TRADING_MODE=live AND LIVE_TRADING_ENABLED=true AND confirm=true.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from alphaquant_data.adapters.mexc_futures import MexcFuturesAdapter
from alphaquant_data.adapters.mexc_private import MexcPrivateClient, coins_to_contract_vol
from alphaquant_db.session import get_session_factory
from alphaquant_risk.engine import RiskEngine, RiskEngineConfig
from alphaquant_services.journaling import persist_signal
from alphaquant_services.notifications import notify_signal
from alphaquant_shared.config import get_settings
from alphaquant_shared.errors import ConfigurationError, RiskViolationError
from alphaquant_shared.logging import get_logger
from alphaquant_shared.types import Side, SignalAction, TradeIdea, TradingMode
from alphaquant_strategies.confluence.engine import ConfluenceEngine

logger = get_logger(__name__)


@dataclass
class LivePreview:
    idea: TradeIdea
    confirm_token: str
    mexc_symbol: str
    contract_vol: float
    contract_size: float
    open_type: int
    disclaimer: str


# In-memory pending confirms (single-node). Redis later for multi-instance.
_PENDING: dict[str, LivePreview] = {}


class LiveExecutionService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _assert_live_armed(self) -> None:
        if self.settings.trading_mode != "live":
            raise ConfigurationError(
                "TRADING_MODE must be 'live' for real orders (currently "
                f"'{self.settings.trading_mode}')"
            )
        if not self.settings.live_trading_enabled:
            raise ConfigurationError(
                "LIVE_TRADING_ENABLED must be true. This is a second safety switch "
                "so live mode is never accidental."
            )
        if not self.settings.mexc_api_key or not self.settings.mexc_api_secret:
            raise ConfigurationError("Set MEXC_API_KEY and MEXC_API_SECRET for live trading")

    def _risk_engine(self) -> RiskEngine:
        s = self.settings
        return RiskEngine(
            RiskEngineConfig(
                risk_per_trade_pct=s.risk_per_trade_pct,
                hard_cap_pct=s.risk_per_trade_hard_cap_pct,
                max_concurrent_risk_pct=s.max_concurrent_risk_pct,
                daily_loss_limit_pct=s.daily_loss_limit_pct,
                min_risk_reward=s.min_risk_reward,
                margin_mode=s.margin_mode,
                max_leverage=s.max_leverage,
                target_leverage=s.target_leverage,
                use_fixed_leverage=s.use_fixed_leverage,
                leverage_safety_buffer=s.leverage_safety_buffer,
                stop_liq_buffer_fraction=s.stop_liq_buffer_fraction,
                maintenance_margin_rate=s.maintenance_margin_rate,
            )
        )

    async def preview(
        self,
        *,
        idea: TradeIdea,
    ) -> LivePreview:
        """Validate idea + size for MEXC. Does NOT place an order."""
        self._assert_live_armed()
        if idea.action == SignalAction.NO_TRADE or idea.side is None or idea.entry is None:
            raise RiskViolationError("Cannot preview NO TRADE / incomplete idea")
        if idea.risk is None:
            raise RiskViolationError("Trade idea missing risk plan")
        if idea.confidence < self.settings.min_confidence:
            raise RiskViolationError("Confidence below live minimum")

        pub = MexcFuturesAdapter(self.settings)
        private = MexcPrivateClient(self.settings)
        try:
            mexc_symbol = pub.normalize_symbol(idea.symbol)
            detail = await private.get_contract_detail(mexc_symbol)
            contract_size = float(
                detail.get("contractSize")
                or detail.get("cs")
                or detail.get("contract_size")
                or 1.0
            )
            vol = coins_to_contract_vol(idea.risk.position_size, contract_size)
            if vol <= 0:
                raise RiskViolationError("Computed contract vol <= 0 — increase equity or tighten stop")

            open_type = 2 if self.settings.margin_mode == "cross" else 1
            token = secrets.token_urlsafe(24)
            preview = LivePreview(
                idea=idea.model_copy(
                    update={"trading_mode": TradingMode.LIVE}
                ),
                confirm_token=token,
                mexc_symbol=mexc_symbol,
                contract_vol=vol,
                contract_size=contract_size,
                open_type=open_type,
                disclaimer=(
                    "REAL MONEY. Confirm places a live MEXC order. "
                    "200x CROSS can lose more than 0.5% if liquidated. "
                    "No profit is guaranteed. Autopilot is OFF."
                ),
            )
            _PENDING[token] = preview
            logger.info(
                "live_preview_ready",
                symbol=mexc_symbol,
                vol=vol,
                side=idea.side.value,
                leverage=idea.risk.suggested_leverage,
            )
            return preview
        finally:
            await pub.close()
            await private.close()

    async def confirm(self, *, confirm_token: str, typed_yes: str) -> dict:
        """Place live order only if token valid and user typed YES."""
        self._assert_live_armed()
        if typed_yes.strip().upper() != "YES":
            raise ConfigurationError("Type YES exactly to confirm live order")

        preview = _PENDING.pop(confirm_token, None)
        if preview is None:
            raise ConfigurationError("Invalid or expired confirm token — preview again")

        idea = preview.idea
        assert idea.risk is not None and idea.side is not None and idea.entry is not None

        private = MexcPrivateClient(self.settings)
        try:
            leverage = int(round(idea.risk.suggested_leverage))
            result = await private.place_order(
                symbol=preview.mexc_symbol,
                side=idea.side,
                price=float(idea.entry),
                vol=preview.contract_vol,
                leverage=leverage,
                open_type=preview.open_type,
                order_type=5,  # market
                stop_loss=float(idea.risk.stop_loss),
                take_profit=float(idea.risk.take_profit_1),
                external_oid=f"aq-{confirm_token[:16]}",
            )
            order_id = None
            data = result.get("data") if isinstance(result, dict) else None
            if isinstance(data, dict):
                order_id = data.get("orderId")
            elif isinstance(data, str):
                order_id = data

            SessionLocal = get_session_factory()
            with SessionLocal() as session:
                persist_signal(session, idea)
                session.commit()

            await notify_signal(idea, telegram=True, discord=True)
            logger.info(
                "live_order_placed",
                symbol=preview.mexc_symbol,
                order_id=order_id,
                at=datetime.now(timezone.utc).isoformat(),
            )
            return {
                "status": "submitted",
                "order_id": order_id,
                "mexc_response": result,
                "symbol": preview.mexc_symbol,
                "vol": preview.contract_vol,
                "side": idea.side.value,
                "leverage": leverage,
                "margin_mode": idea.risk.margin_mode.value if idea.risk.margin_mode else "cross",
                "note": "Order submitted to MEXC. Verify in MEXC app/positions. Not a profit guarantee.",
            }
        finally:
            await private.close()


async def build_live_idea_from_evaluate(
    *,
    symbol: str,
    side: Side,
    entry: float,
    stop_loss: float,
    account_equity: float,
    confluence_labels: list[str],
    timeframes: list[tuple[str, str]],
) -> TradeIdea:
    """Reuse confluence engine under LIVE trading_mode label for journaling."""
    from alphaquant_indicators.structure.swings import MarketBias
    from alphaquant_shared.types import ConfluenceItem, Timeframe, timeframe_from_str
    from alphaquant_strategies.confluence.engine import ConfluenceInput, TimeframeSnapshot

    engine = ConfluenceEngine(trading_mode=TradingMode.LIVE)
    snapshots = [
        TimeframeSnapshot(timeframe_from_str(tf), MarketBias(bias.lower()))
        for tf, bias in timeframes
    ]
    confluences = [
        ConfluenceItem(code=f"c{i}", label=label, bullish=True)
        for i, label in enumerate(confluence_labels)
    ]
    return engine.evaluate(
        ConfluenceInput(
            symbol=symbol,
            entry=entry,
            stop_loss=stop_loss,
            side=side,
            account_equity=account_equity,
            timeframe_snapshots=snapshots,
            confluences=confluences,
        )
    )
