"""Data ingestion helpers."""

from __future__ import annotations

from alphaquant_data.adapters.base import ExchangeAdapter
from alphaquant_data.caching import MemoryKlineCache, kline_cache_key
from alphaquant_shared.types import Candle, Timeframe


async def fetch_klines_cached(
    adapter: ExchangeAdapter,
    symbol: str,
    timeframe: Timeframe,
    *,
    limit: int = 500,
    cache: MemoryKlineCache | None = None,
    ttl_s: float = 30.0,
) -> list[Candle]:
    """Fetch klines with optional memory cache (Redis wired later)."""
    cache = cache or MemoryKlineCache()
    key = kline_cache_key(adapter.capabilities.name, symbol, timeframe)
    hit = cache.get(key)
    if hit is not None and len(hit) >= min(limit, len(hit)):
        return hit[-limit:]
    candles = await adapter.get_klines(symbol, timeframe, limit=limit)
    cache.set(key, candles, ttl_s=ttl_s)
    return candles
