"""Risk engine unit tests — 200x + ≤0.5% wallet, stop before liquidation."""

from __future__ import annotations

import pytest

from alphaquant_risk.engine import RiskEngine, RiskEngineConfig
from alphaquant_risk.liquidation import (
    estimate_liquidation_price,
    max_stop_distance_before_liquidation,
    stop_is_before_liquidation,
)
from alphaquant_risk.sizing import calculate_position_size, calculate_position_size_detailed
from alphaquant_risk.stops import build_stop_take_profit_plan, risk_reward_ratio
from alphaquant_shared.errors import RiskViolationError
from alphaquant_shared.types import Side


def test_position_size_half_percent_stop_mode():
    qty, notional, eff = calculate_position_size(
        account_equity=10_000,
        risk_pct=0.005,
        entry=100,
        stop_loss=98,
        hard_cap_pct=0.005,
    )
    assert qty == pytest.approx(25)
    assert notional == pytest.approx(2500)
    assert eff == 0.005


def test_200x_margin_caps_wallet_loss_at_half_percent():
    """Isolated margin = 0.5% wallet → liq wipe cannot exceed that slice."""
    sized = calculate_position_size_detailed(
        account_equity=10_000,
        risk_pct=0.005,
        entry=2000,
        stop_loss=1999,  # very tight stop
        leverage=200,
        hard_cap_pct=0.005,
        use_leverage_margin_cap=True,
    )
    assert sized.effective_risk_pct == 0.005
    assert sized.leverage == 200
    assert sized.isolated_margin == pytest.approx(50.0, rel=1e-6)


def test_risk_hard_cap_rejects_above_half_percent_via_engine():
    engine = RiskEngine()
    entry, stop = 2000.0, 1999.0
    with pytest.raises(RiskViolationError, match="0.5%"):
        engine.build_plan(
            side=Side.LONG,
            entry=entry,
            stop_loss=stop,
            account_equity=10_000,
            risk_pct=0.01,
        )


def test_wide_stop_rejected_at_200x():
    engine = RiskEngine()
    with pytest.raises(RiskViolationError, match="200"):
        engine.build_plan(
            side=Side.LONG,
            entry=3600,
            stop_loss=3550,  # far beyond 200x liq
            account_equity=10_000,
        )


def test_engine_plan_200x_tight_stop_cross_default():
    engine = RiskEngine()  # default CROSS
    entry = 2000.0
    max_dist = max_stop_distance_before_liquidation(entry=entry, leverage=200)
    stop = entry - max_dist * 0.8
    plan = engine.build_plan(
        side=Side.LONG, entry=entry, stop_loss=stop, account_equity=10_000
    )
    assert plan.suggested_leverage == 200
    assert plan.margin_mode.value == "cross"
    assert plan.risk_pct == pytest.approx(0.005)
    assert plan.position_margin is not None
    assert plan.liquidation_warning is True  # cross always caution-flagged
    assert "CROSS" in (plan.liquidation_warning_note or "")
    assert plan.liquidation_price < stop < entry


def test_isolated_mode_caps_note():
    engine = RiskEngine(RiskEngineConfig(margin_mode="isolated"))
    entry = 2000.0
    max_dist = max_stop_distance_before_liquidation(entry=entry, leverage=200)
    stop = entry - max_dist * 0.5
    plan = engine.build_plan(
        side=Side.LONG, entry=entry, stop_loss=stop, account_equity=10_000
    )
    assert plan.margin_mode.value == "isolated"
    assert "ISOLATED" in (plan.liquidation_warning_note or "")


def test_long_liq_at_200x_not_zero():
    liq = estimate_liquidation_price(side=Side.LONG, entry=3625, leverage=200)
    assert liq > 3600
    assert liq < 3625
    assert abs(liq - 3625) / 3625 < 0.01  # within ~1%


def test_zero_stop_raises():
    with pytest.raises(RiskViolationError):
        calculate_position_size(
            account_equity=10_000, risk_pct=0.005, entry=100, stop_loss=100
        )


def test_rr_and_tp_ladder():
    plan = build_stop_take_profit_plan(side=Side.LONG, entry=100, stop_loss=99.9)
    assert plan.risk_reward_to_tp1 == 2.0
    assert risk_reward_ratio(entry=100, stop_loss=99.9, take_profit=plan.take_profit_1) == (
        pytest.approx(2.0)
    )


def test_daily_loss_halt():
    engine = RiskEngine(RiskEngineConfig(daily_loss_limit_pct=0.015))
    engine.record_realized_pnl_pct(-0.016)
    assert engine.trading_halted_today
    entry = 2000.0
    stop = entry - max_stop_distance_before_liquidation(entry=entry, leverage=200) * 0.5
    with pytest.raises(RiskViolationError, match="Daily loss"):
        engine.build_plan(side=Side.LONG, entry=entry, stop_loss=stop, account_equity=10_000)
