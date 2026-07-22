"""Backtesting metrics (Phase 5 scaffold — compute helpers only)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BacktestMetrics:
    trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe: float
    sortino: float
    expectancy: float


def compute_metrics(returns: list[float], *, periods_per_year: float = 365.0) -> BacktestMetrics:
    """Compute standard metrics from per-trade returns (fractional, e.g. 0.01 = +1%)."""
    if not returns:
        return BacktestMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    arr = np.asarray(returns, dtype=float)
    wins = arr[arr > 0]
    losses = arr[arr < 0]
    win_rate = float(len(wins) / len(arr))
    gross_profit = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    equity = np.cumprod(1.0 + arr)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(dd.min()) if len(dd) else 0.0

    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    downside = arr[arr < 0]
    downside_std = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sharpe = (mean / std) * np.sqrt(periods_per_year) if std > 0 else 0.0
    sortino = (mean / downside_std) * np.sqrt(periods_per_year) if downside_std > 0 else 0.0
    expectancy = float(mean)

    return BacktestMetrics(
        trades=len(arr),
        win_rate=win_rate,
        profit_factor=float(profit_factor) if np.isfinite(profit_factor) else 999.0,
        max_drawdown=max_dd,
        sharpe=float(sharpe),
        sortino=float(sortino),
        expectancy=expectancy,
    )
