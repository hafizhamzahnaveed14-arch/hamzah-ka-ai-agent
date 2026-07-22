"""Risk Engine — MEXC style: 200x leverage, ≤0.5% wallet, stop before liq."""

from __future__ import annotations

from dataclasses import dataclass, field

from alphaquant_risk.liquidation import (
    estimate_liquidation_price,
    liquidation_near_stop,
    max_stop_distance_before_liquidation,
    stop_is_before_liquidation,
    suggest_conservative_leverage,
)
from alphaquant_risk.sizing import calculate_position_size_detailed
from alphaquant_risk.stops import build_stop_take_profit_plan, risk_reward_ratio
from alphaquant_shared.errors import RiskViolationError
from alphaquant_shared.types import MarginMode, RiskPlan, Side


@dataclass
class RiskEngineConfig:
    # Wallet risk budget for stop / initial margin sizing (≤ 0.5%)
    risk_per_trade_pct: float = 0.005
    hard_cap_pct: float = 0.005
    max_concurrent_risk_pct: float = 0.015
    daily_loss_limit_pct: float = 0.015
    min_risk_reward: float = 2.0
    # User preference: CROSS on MEXC (shared wallet margin)
    margin_mode: str = "cross"  # "cross" | "isolated"
    target_leverage: float = 200.0
    max_leverage: float = 200.0
    use_fixed_leverage: bool = True
    maintenance_margin_rate: float = 0.004
    stop_liq_buffer_fraction: float = 0.6
    require_stop_before_liquidation: bool = True
    leverage_safety_buffer: float = 3.0
    min_leverage: float = 1.25
    liquidation_proximity_factor: float = 1.15


@dataclass
class RiskEngine:
    """Capital constraints. Default margin mode: CROSS + 200x (see warnings)."""

    config: RiskEngineConfig = field(default_factory=RiskEngineConfig)
    open_risk_pct: float = 0.0
    realized_pnl_pct_today: float = 0.0
    trading_halted_today: bool = False

    def register_open_risk(self, risk_pct: float) -> None:
        self.open_risk_pct += risk_pct

    def release_open_risk(self, risk_pct: float) -> None:
        self.open_risk_pct = max(0.0, self.open_risk_pct - risk_pct)

    def record_realized_pnl_pct(self, pnl_pct: float) -> None:
        self.realized_pnl_pct_today += pnl_pct
        if self.realized_pnl_pct_today <= -abs(self.config.daily_loss_limit_pct):
            self.trading_halted_today = True

    def reset_daily(self) -> None:
        self.realized_pnl_pct_today = 0.0
        self.trading_halted_today = False

    def assert_can_open(self, additional_risk_pct: float) -> None:
        if self.trading_halted_today:
            raise RiskViolationError("Daily loss limit reached — trading halted for the day")
        projected = self.open_risk_pct + additional_risk_pct
        if projected > self.config.max_concurrent_risk_pct + 1e-12:
            raise RiskViolationError(
                f"Concurrent risk {projected:.4%} exceeds max "
                f"{self.config.max_concurrent_risk_pct:.4%}"
            )

    def build_plan(
        self,
        *,
        side: Side,
        entry: float,
        stop_loss: float,
        account_equity: float,
        risk_pct: float | None = None,
        rr_targets: tuple[float, float, float] = (2.0, 3.0, 4.5),
    ) -> RiskPlan:
        if self.trading_halted_today:
            raise RiskViolationError("Daily loss limit reached — trading halted for the day")

        requested = self.config.risk_per_trade_pct if risk_pct is None else risk_pct
        if requested > self.config.hard_cap_pct + 1e-15:
            raise RiskViolationError(
                f"Requested risk {requested:.4%} exceeds hard cap "
                f"{self.config.hard_cap_pct:.4%} (max 0.5% of wallet)"
            )

        leverage = suggest_conservative_leverage(
            entry=entry,
            stop_loss=stop_loss,
            side=side,
            safety_buffer=self.config.leverage_safety_buffer,
            max_leverage=self.config.max_leverage,
            maintenance_margin_rate=self.config.maintenance_margin_rate,
            min_leverage=self.config.min_leverage,
            fixed_leverage=(
                self.config.target_leverage if self.config.use_fixed_leverage else None
            ),
        )

        liq = estimate_liquidation_price(
            side=side,
            entry=entry,
            leverage=leverage,
            maintenance_margin_rate=self.config.maintenance_margin_rate,
        )
        if side == Side.LONG and liq <= 0:
            raise RiskViolationError("Long liquidation price invalid (<= 0)")

        stop_dist = abs(entry - stop_loss)
        max_dist = max_stop_distance_before_liquidation(
            entry=entry,
            leverage=leverage,
            maintenance_margin_rate=self.config.maintenance_margin_rate,
            buffer_fraction=self.config.stop_liq_buffer_fraction,
        )

        if self.config.require_stop_before_liquidation:
            if not stop_is_before_liquidation(
                side=side, entry=entry, stop_loss=stop_loss, liquidation_price=liq
            ):
                raise RiskViolationError(
                    f"At {leverage:.0f}x, stop must sit BEFORE liquidation so liq never "
                    f"triggers. Liq≈{liq:.6g}, stop={stop_loss}. "
                    f"Max safe stop distance ≈ {max_dist:.6g} "
                    f"({max_dist / entry * 100:.3f}% of entry). "
                    f"Widen is not allowed — tighten stop or NO TRADE."
                )
            if stop_dist > max_dist + 1e-12:
                raise RiskViolationError(
                    f"Stop too wide for {leverage:.0f}x without hitting liquidation. "
                    f"Stop distance {stop_dist:.6g} > max safe {max_dist:.6g}. "
                    f"Use a tighter stop or NO TRADE (wallet risk stays ≤0.5% either way)."
                )

        sized = calculate_position_size_detailed(
            account_equity=account_equity,
            risk_pct=requested,
            entry=entry,
            stop_loss=stop_loss,
            leverage=leverage,
            hard_cap_pct=self.config.hard_cap_pct,
            use_leverage_margin_cap=True,
        )
        self.assert_can_open(sized.effective_risk_pct)

        stp = build_stop_take_profit_plan(
            side=side, entry=entry, stop_loss=stop_loss, rr_targets=rr_targets
        )
        rr = risk_reward_ratio(
            entry=entry, stop_loss=stop_loss, take_profit=stp.take_profit_1
        )
        if rr + 1e-12 < self.config.min_risk_reward:
            raise RiskViolationError(
                f"Risk:Reward {rr:.2f} < minimum {self.config.min_risk_reward}"
            )

        warn = liquidation_near_stop(
            side=side,
            entry=entry,
            stop_loss=stop_loss,
            liquidation_price=liq,
            proximity_factor=self.config.liquidation_proximity_factor,
        )

        mode = (
            MarginMode.CROSS
            if self.config.margin_mode.lower() == "cross"
            else MarginMode.ISOLATED
        )
        margin_amt = round(sized.isolated_margin, 6)

        if mode == MarginMode.ISOLATED:
            note = (
                f"ISOLATED init margin ≈ {margin_amt} "
                f"({sized.effective_risk_pct * 100:.2f}% wallet). "
                f"Wipe on this position is roughly capped near that margin. "
                f"Stop before liq so liquidation should not trigger."
            )
            # Isolated: margin wipe ≈ budget — warning only if stop near liq
        else:
            note = (
                f"CROSS init margin ≈ {margin_amt} "
                f"({sized.effective_risk_pct * 100:.2f}% wallet). "
                f"CROSS shares the whole wallet — liquidation can take MORE than 0.5%. "
                f"Stop must fire before liq; never rely on margin size alone."
            )
            # Cross always surfaces as elevated caution in the plan note
            warn = True

        if warn and mode == MarginMode.ISOLATED:
            note += " Stop is close to liquidation — keep stop inside the safe buffer."

        return RiskPlan(
            account_equity=account_equity,
            risk_pct=sized.effective_risk_pct,
            position_size=round(sized.qty, 8),
            position_notional=round(sized.notional, 4),
            margin_mode=mode,
            position_margin=margin_amt,
            isolated_margin=margin_amt,
            stop_loss=stp.stop_loss,
            take_profit_1=round(stp.take_profit_1, 8),
            take_profit_2=round(stp.take_profit_2, 8),
            take_profit_3=round(stp.take_profit_3, 8),
            risk_reward=round(rr, 4),
            suggested_leverage=leverage,
            liquidation_price=round(liq, 8),
            liquidation_warning=warn,
            liquidation_warning_note=note,
        )
