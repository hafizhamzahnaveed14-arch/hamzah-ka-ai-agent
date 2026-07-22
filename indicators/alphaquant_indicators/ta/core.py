"""Core TA indicators implemented with NumPy/Pandas (causal only — no future leak)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _as_series(values: pd.Series | np.ndarray | list[float], name: str = "x") -> pd.Series:
    if isinstance(values, pd.Series):
        return values.astype(float)
    return pd.Series(values, dtype=float, name=name)


def sma(values: pd.Series | np.ndarray | list[float], period: int) -> pd.Series:
    s = _as_series(values)
    return s.rolling(window=period, min_periods=period).mean()


def ema(values: pd.Series | np.ndarray | list[float], period: int) -> pd.Series:
    s = _as_series(values)
    return s.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(closes: pd.Series | np.ndarray | list[float], period: int = 14) -> pd.Series:
    s = _as_series(closes, "close")
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    # When avg_loss == 0 (strictly rising), RSI is defined as 100.
    rs = avg_gain / avg_loss
    out = np.where(avg_loss == 0, 100.0, 100.0 - (100.0 / (1.0 + rs)))
    result = pd.Series(out, index=s.index, name="rsi")
    result.iloc[:period] = np.nan
    return result


def atr(
    high: pd.Series | np.ndarray | list[float],
    low: pd.Series | np.ndarray | list[float],
    close: pd.Series | np.ndarray | list[float],
    period: int = 14,
) -> pd.Series:
    h, l, c = _as_series(high, "h"), _as_series(low, "l"), _as_series(close, "c")
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().rename("atr")


def macd(
    closes: pd.Series | np.ndarray | list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    c = _as_series(closes, "close")
    line = ema(c, fast) - ema(c, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = line - sig
    return pd.DataFrame({"macd": line, "signal": sig, "hist": hist})


def bollinger(
    closes: pd.Series | np.ndarray | list[float],
    period: int = 20,
    std_mult: float = 2.0,
) -> pd.DataFrame:
    c = _as_series(closes, "close")
    mid = sma(c, period)
    std = c.rolling(window=period, min_periods=period).std()
    return pd.DataFrame(
        {"mid": mid, "upper": mid + std_mult * std, "lower": mid - std_mult * std}
    )


def vwap(
    high: pd.Series | np.ndarray | list[float],
    low: pd.Series | np.ndarray | list[float],
    close: pd.Series | np.ndarray | list[float],
    volume: pd.Series | np.ndarray | list[float],
) -> pd.Series:
    h, l, c, v = _as_series(high), _as_series(low), _as_series(close), _as_series(volume)
    typical = (h + l + c) / 3.0
    cum_vol = v.cumsum().replace(0, np.nan)
    return ((typical * v).cumsum() / cum_vol).rename("vwap")


def stochastic_rsi(
    closes: pd.Series | np.ndarray | list[float],
    rsi_period: int = 14,
    stoch_period: int = 14,
) -> pd.Series:
    r = rsi(closes, rsi_period)
    lowest = r.rolling(stoch_period, min_periods=stoch_period).min()
    highest = r.rolling(stoch_period, min_periods=stoch_period).max()
    return ((r - lowest) / (highest - lowest).replace(0, np.nan) * 100).rename("stoch_rsi")


def adx(
    high: pd.Series | np.ndarray | list[float],
    low: pd.Series | np.ndarray | list[float],
    close: pd.Series | np.ndarray | list[float],
    period: int = 14,
) -> pd.Series:
    h, l, c = _as_series(high), _as_series(low), _as_series(close)
    up = h.diff()
    down = -l.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = atr(h, l, c, period)
    plus_di = (
        100
        * pd.Series(plus_dm, index=h.index)
        .ewm(alpha=1 / period, adjust=False, min_periods=period)
        .mean()
        / tr
    )
    minus_di = (
        100
        * pd.Series(minus_dm, index=h.index)
        .ewm(alpha=1 / period, adjust=False, min_periods=period)
        .mean()
        / tr
    )
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().rename("adx")
