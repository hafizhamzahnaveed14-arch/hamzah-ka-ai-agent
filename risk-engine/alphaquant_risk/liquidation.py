"""Liquidation helpers for high-leverage (e.g. MEXC 200x) isolated futures."""

from __future__ import annotations

from alphaquant_shared.errors import RiskViolationError
from alphaquant_shared.types import Side


def estimate_liquidation_price(
    *,
    side: Side,
    entry: float,
    leverage: float,
    maintenance_margin_rate: float = 0.004,
) -> float:
    """Approximate isolated-margin liquidation (simplified linear futures).

    LONG:  entry * (1 - 1/leverage + mmr)
    SHORT: entry * (1 + 1/leverage - mmr)

    At 200x, long liq is close to entry (e.g. ~0.1–0.5% away) — never 0.000
    unless leverage/inputs are invalid.
    """
    if entry <= 0:
        raise RiskViolationError("entry must be positive")
    if leverage < 1:
        raise RiskViolationError("leverage must be >= 1")
    if maintenance_margin_rate < 0:
        raise RiskViolationError("maintenance_margin_rate must be >= 0")

    inv = 1.0 / leverage
    if side == Side.LONG:
        price = entry * (1.0 - inv + maintenance_margin_rate)
        if price <= 0:
            raise RiskViolationError(
                "Computed long liquidation <= 0 — check leverage / mmr inputs"
            )
        return price
    price = entry * (1.0 + inv - maintenance_margin_rate)
    if price <= entry:
        raise RiskViolationError("Computed short liquidation is on the wrong side of entry")
    return price


def max_stop_distance_before_liquidation(
    *,
    entry: float,
    leverage: float,
    maintenance_margin_rate: float = 0.004,
    buffer_fraction: float = 0.6,
) -> float:
    """Max |entry - stop| so the stop is hit before liquidation (with buffer).

    At 200x, this distance is small — wide structural stops are incompatible
    with "never liquidate" and must become NO TRADE.
    """
    if entry <= 0 or leverage < 1:
        raise RiskViolationError("invalid entry/leverage")
    # Distance from entry to liq ≈ entry * (1/L - mmr) for longs (same mag. shorts)
    raw = entry * max(0.0, (1.0 / leverage) - maintenance_margin_rate)
    return raw * buffer_fraction


def stop_is_before_liquidation(
    *,
    side: Side,
    entry: float,
    stop_loss: float,
    liquidation_price: float,
) -> bool:
    """True if stop sits between entry and liquidation (exit before wipe)."""
    if side == Side.LONG:
        return liquidation_price < stop_loss < entry
    return entry < stop_loss < liquidation_price


def suggest_conservative_leverage(
    *,
    entry: float,
    stop_loss: float,
    side: Side = Side.LONG,
    safety_buffer: float = 3.0,
    max_leverage: float = 200.0,
    maintenance_margin_rate: float = 0.004,
    min_leverage: float = 1.25,
    fixed_leverage: float | None = None,
) -> float:
    """Return fixed target leverage when set (e.g. 200), else derive from stop."""
    if fixed_leverage is not None:
        if fixed_leverage < 1:
            raise RiskViolationError("fixed_leverage must be >= 1")
        return round(min(fixed_leverage, max_leverage), 2)

    if entry <= 0:
        raise RiskViolationError("entry must be positive")
    stop_pct = abs(entry - stop_loss) / entry
    if stop_pct <= 0:
        raise RiskViolationError("stop distance must be > 0")

    denom = safety_buffer * stop_pct + maintenance_margin_rate
    raw = 1.0 / denom
    return round(max(min_leverage, min(max_leverage, raw)), 2)


def liquidation_near_stop(
    *,
    side: Side,
    entry: float,
    stop_loss: float,
    liquidation_price: float,
    proximity_factor: float = 1.2,
) -> bool:
    """True if stop and liquidation are uncomfortably close."""
    if liquidation_price <= 0:
        return True
    if not stop_is_before_liquidation(
        side=side, entry=entry, stop_loss=stop_loss, liquidation_price=liquidation_price
    ):
        return True
    stop_dist = abs(entry - stop_loss)
    liq_dist = abs(entry - liquidation_price)
    if stop_dist <= 0:
        return True
    # Warn if stop uses most of the room to liquidation
    return stop_dist >= liq_dist / proximity_factor
