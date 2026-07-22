"""Volume analysis helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VolumeSpike:
    index: int
    volume: float
    ratio_vs_avg: float


def detect_volume_spikes(
    volume: pd.Series | np.ndarray | list[float],
    *,
    lookback: int = 20,
    mult: float = 2.0,
) -> list[VolumeSpike]:
    v = pd.Series(np.asarray(volume, dtype=float))
    avg = v.rolling(lookback, min_periods=max(5, lookback // 2)).mean()
    spikes: list[VolumeSpike] = []
    for i in range(len(v)):
        if pd.isna(avg.iloc[i]) or avg.iloc[i] <= 0:
            continue
        ratio = float(v.iloc[i] / avg.iloc[i])
        if ratio >= mult:
            spikes.append(VolumeSpike(index=i, volume=float(v.iloc[i]), ratio_vs_avg=ratio))
    return spikes


def approximate_delta(
    open_: pd.Series | np.ndarray | list[float],
    close: pd.Series | np.ndarray | list[float],
    volume: pd.Series | np.ndarray | list[float],
) -> pd.Series:
    """Proxy delta when true aggressor volume is unavailable: sign(close-open)*volume."""
    o = np.asarray(open_, dtype=float)
    c = np.asarray(close, dtype=float)
    v = np.asarray(volume, dtype=float)
    sign = np.sign(c - o)
    sign[sign == 0] = 0.0
    return pd.Series(sign * v, name="approx_delta")
