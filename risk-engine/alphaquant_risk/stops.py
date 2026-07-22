"""Stop-loss and multi-target take-profit helpers."""

from __future__ import annotations

from dataclasses import dataclass

from alphaquant_shared.errors import RiskViolationError
from alphaquant_shared.types import Side


@dataclass(frozen=True)
class StopTakeProfitPlan:
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward_to_tp1: float
    risk_reward_to_tp2: float
    risk_reward_to_tp3: float


def build_stop_take_profit_plan(
    *,
    side: Side,
    entry: float,
    stop_loss: float,
    rr_targets: tuple[float, float, float] = (2.0, 3.0, 4.5),
) -> StopTakeProfitPlan:
    """Build TP ladder from stop distance and RR multiples.

    Default TP1 is at least 2R to satisfy the hard RR gate when using TP1.
    """
    if entry <= 0 or stop_loss <= 0:
        raise RiskViolationError("entry and stop_loss must be positive")

    risk = abs(entry - stop_loss)
    if risk <= 0:
        raise RiskViolationError("stop distance must be > 0")

    if side == Side.LONG and stop_loss >= entry:
        raise RiskViolationError("LONG stop_loss must be below entry")
    if side == Side.SHORT and stop_loss <= entry:
        raise RiskViolationError("SHORT stop_loss must be above entry")

    direction = 1.0 if side == Side.LONG else -1.0
    tps = [entry + direction * risk * rr for rr in rr_targets]
    return StopTakeProfitPlan(
        stop_loss=stop_loss,
        take_profit_1=tps[0],
        take_profit_2=tps[1],
        take_profit_3=tps[2],
        risk_reward_to_tp1=rr_targets[0],
        risk_reward_to_tp2=rr_targets[1],
        risk_reward_to_tp3=rr_targets[2],
    )


def risk_reward_ratio(*, entry: float, stop_loss: float, take_profit: float) -> float:
    risk = abs(entry - stop_loss)
    if risk <= 0:
        raise RiskViolationError("stop distance must be > 0")
    reward = abs(take_profit - entry)
    return reward / risk
