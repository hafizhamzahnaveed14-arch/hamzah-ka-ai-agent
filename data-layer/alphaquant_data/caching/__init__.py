"""Redis-backed OHLCV cache helpers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from alphaquant_shared.types import Candle, Timeframe


def kline_cache_key(exchange: str, symbol: str, timeframe: Timeframe) -> str:
    return f"aq:klines:{exchange}:{symbol.upper()}:{timeframe.value}"


def candles_to_payload(candles: list[Candle]) -> str:
    return json.dumps([c.model_dump(mode="json") for c in candles])


def candles_from_payload(payload: str) -> list[Candle]:
    raw: list[dict[str, Any]] = json.loads(payload)
    return [Candle.model_validate(item) for item in raw]


class MemoryKlineCache:
    """In-process cache used when Redis is unavailable (dev / tests)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def set(self, key: str, candles: list[Candle], *, ttl_s: float = 60.0) -> None:
        import time

        self._store[key] = (time.monotonic() + ttl_s, candles_to_payload(candles))

    def get(self, key: str) -> list[Candle] | None:
        import time

        item = self._store.get(key)
        if item is None:
            return None
        expires, payload = item
        if time.monotonic() > expires:
            del self._store[key]
            return None
        return candles_from_payload(payload)

    def clear(self) -> None:
        self._store.clear()
