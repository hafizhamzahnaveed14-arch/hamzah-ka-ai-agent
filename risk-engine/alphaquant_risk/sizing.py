"""Position sizing — wallet risk cap + optional high-leverage isolated margin.

User rule (MEXC): up to 200x leverage, but wallet risk ≤ 0.5% so even a
full isolated-margin wipe cannot take more than that slice of the account.
"""

from __future__ import annotations

from dataclasses import dataclass

from alphaquant_shared.errors import RiskViolationError


@dataclass(frozen=True)
class PositionSizeResult:
    qty: float
    notional: float
    effective_risk_pct: float
    isolated_margin: float
    leverage: float
    sized_by: str  # "stop" | "margin" | "min(stop,margin)"


def calculate_position_size(
    *,
    account_equity: float,
    risk_pct: float,
    entry: float,
    stop_loss: float,
    hard_cap_pct: float = 0.005,
) -> tuple[float, float, float]:
    """Legacy stop-distance sizing. Return (qty, notional, effective_risk_pct)."""
    result = calculate_position_size_detailed(
        account_equity=account_equity,
        risk_pct=risk_pct,
        entry=entry,
        stop_loss=stop_loss,
        leverage=1.0,
        hard_cap_pct=hard_cap_pct,
        use_leverage_margin_cap=False,
    )
    return result.qty, result.notional, result.effective_risk_pct


def calculate_position_size_detailed(
    *,
    account_equity: float,
    risk_pct: float,
    entry: float,
    stop_loss: float,
    leverage: float,
    hard_cap_pct: float = 0.005,
    use_leverage_margin_cap: bool = True,
) -> PositionSizeResult:
    """Size so stop-loss AND isolated-margin liquidation both stay ≤ risk budget.

    - ``risk_cash = equity * min(risk_pct, hard_cap)``  (≤ 0.5% wallet)
    - Stop sizing: qty_stop = risk_cash / |entry - stop|
    - Margin sizing at leverage L: margin = risk_cash, notional = margin * L,
      qty_margin = notional / entry
      → if liquidated on isolated margin, loss ≈ margin ≤ 0.5% wallet
    - Final qty = min(qty_stop, qty_margin) when leverage cap is on
    """
    if account_equity <= 0:
        raise RiskViolationError("account_equity must be positive")
    if entry <= 0 or stop_loss <= 0:
        raise RiskViolationError("entry and stop_loss must be positive")
    if risk_pct <= 0:
        raise RiskViolationError("risk_pct must be positive")
    if leverage < 1:
        raise RiskViolationError("leverage must be >= 1")

    effective = min(risk_pct, hard_cap_pct)
    stop_distance = abs(entry - stop_loss)
    if stop_distance <= 0:
        raise RiskViolationError("stop distance must be > 0")

    risk_cash = account_equity * effective
    qty_stop = risk_cash / stop_distance

    if not use_leverage_margin_cap or leverage <= 1.0:
        return PositionSizeResult(
            qty=qty_stop,
            notional=qty_stop * entry,
            effective_risk_pct=effective,
            isolated_margin=qty_stop * entry,  # 1x ≈ full notional as margin
            leverage=leverage,
            sized_by="stop",
        )

    # Isolated margin locked to risk budget → liquidation cannot exceed ~0.5% wallet
    margin = risk_cash
    qty_margin = (margin * leverage) / entry
    qty = min(qty_stop, qty_margin)
    notional = qty * entry
    actual_margin = notional / leverage
    sized_by = "min(stop,margin)" if qty_stop != qty_margin else "margin"
    if qty == qty_stop and qty < qty_margin - 1e-12:
        sized_by = "stop"
    elif qty == qty_margin and qty < qty_stop - 1e-12:
        sized_by = "margin"

    return PositionSizeResult(
        qty=qty,
        notional=notional,
        effective_risk_pct=effective,
        isolated_margin=actual_margin,
        leverage=leverage,
        sized_by=sized_by,
    )
