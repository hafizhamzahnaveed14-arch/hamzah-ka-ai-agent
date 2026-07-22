"""Market data routes (MEXC primary via ExchangeAdapter)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from alphaquant_data.adapters.registry import get_adapter
from alphaquant_shared.errors import ExchangeError, RateLimitError
from alphaquant_shared.types import timeframe_from_str

router = APIRouter()


@router.get("/market/{symbol}/klines")
async def get_klines(
    symbol: str,
    timeframe: str = Query("1h"),
    limit: int = Query(200, ge=1, le=1500),
    exchange: str = Query("mexc"),
):
    try:
        tf = timeframe_from_str(timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    adapter = get_adapter(exchange)
    try:
        candles = await adapter.get_klines(symbol, tf, limit=limit)
        return {
            "exchange": adapter.capabilities.name,
            "symbol": symbol.upper(),
            "timeframe": tf.value,
            "count": len(candles),
            "candles": [c.model_dump(mode="json") for c in candles],
        }
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ExchangeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await adapter.close()


@router.get("/market/{symbol}/ticker")
async def get_ticker(symbol: str, exchange: str = Query("mexc")):
    adapter = get_adapter(exchange)
    try:
        price = await adapter.get_ticker_price(symbol)
        return {"symbol": symbol.upper(), "price": price, "exchange": adapter.capabilities.name}
    except ExchangeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await adapter.close()
