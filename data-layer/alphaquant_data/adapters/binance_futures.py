"""Binance USDT-M Futures adapter (primary venue for Phase 1)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx
import websockets
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from alphaquant_data.adapters.base import CandleHandler, ExchangeAdapter, ExchangeCapabilities
from alphaquant_data.adapters.rate_limit import RateLimiter
from alphaquant_shared.config import Settings, get_settings
from alphaquant_shared.errors import ExchangeError, ExchangeUnavailableError, RateLimitError
from alphaquant_shared.logging import get_logger
from alphaquant_shared.types import Candle, Timeframe

logger = get_logger(__name__)

_TF_TO_BINANCE: dict[Timeframe, str] = {
    Timeframe.M1: "1m",
    Timeframe.M3: "3m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1d",
    Timeframe.W1: "1w",
}


class BinanceFuturesAdapter(ExchangeAdapter):
    """REST + websocket access to Binance USD-M Futures."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.settings.binance_futures_rest,
            timeout=httpx.Timeout(30.0),
        )
        self._limiter = RateLimiter(requests_per_minute=1100)  # under 1200 weight soft budget
        self._closed = False

    @property
    def capabilities(self) -> ExchangeCapabilities:
        return ExchangeCapabilities(
            name="binance_futures",
            supports_futures=True,
            supports_spot=False,
            supports_websocket=True,
            max_requests_per_minute=1200,
        )

    async def close(self) -> None:
        self._closed = True
        if self._owns_client:
            await self._client.aclose()

    async def ping(self) -> bool:
        try:
            await self._limiter.acquire()
            resp = await self._client.get("/fapi/v1/ping")
            return resp.status_code == 200
        except Exception as exc:  # noqa: BLE001 — health checks must not raise
            logger.warning("binance_ping_failed", error=str(exc))
            return False

    async def get_klines(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        limit: int = 500,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Candle]:
        sym = self.normalize_symbol(symbol)
        interval = _TF_TO_BINANCE[timeframe]
        params: dict[str, Any] = {
            "symbol": sym,
            "interval": interval,
            "limit": min(max(limit, 1), 1500),
        }
        if start_time is not None:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time is not None:
            params["endTime"] = int(end_time.timestamp() * 1000)

        data = await self._request_json("GET", "/fapi/v1/klines", params=params)
        candles: list[Candle] = []
        for row in data:
            candles.append(
                Candle(
                    symbol=sym,
                    timeframe=timeframe,
                    open_time=datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    close_time=datetime.fromtimestamp(row[6] / 1000, tz=timezone.utc),
                    quote_volume=float(row[7]),
                    trades=int(row[8]),
                )
            )
        return candles

    async def get_ticker_price(self, symbol: str) -> float:
        sym = self.normalize_symbol(symbol)
        data = await self._request_json(
            "GET", "/fapi/v1/ticker/price", params={"symbol": sym}
        )
        return float(data["price"])

    async def get_funding_rate(self, symbol: str) -> float | None:
        sym = self.normalize_symbol(symbol)
        data = await self._request_json(
            "GET", "/fapi/v1/premiumIndex", params={"symbol": sym}
        )
        rate = data.get("lastFundingRate")
        return float(rate) if rate is not None else None

    async def get_open_interest(self, symbol: str) -> float | None:
        sym = self.normalize_symbol(symbol)
        data = await self._request_json(
            "GET", "/fapi/v1/openInterest", params={"symbol": sym}
        )
        oi = data.get("openInterest")
        return float(oi) if oi is not None else None

    async def subscribe_klines(
        self,
        symbol: str,
        timeframe: Timeframe,
        handler: CandleHandler | None = None,
    ) -> AsyncIterator[Candle]:
        """Reconnecting kline stream. Yields candle updates; prefers closed bars."""
        sym = self.normalize_symbol(symbol).lower()
        interval = _TF_TO_BINANCE[timeframe]
        stream = f"{sym}@kline_{interval}"
        url = f"{self.settings.binance_futures_ws}/ws/{stream}"
        backoff = 1.0
        max_backoff = 60.0

        while not self._closed:
            try:
                logger.info("binance_ws_connecting", stream=stream)
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    backoff = 1.0
                    async for raw in ws:
                        payload = json.loads(raw)
                        k = payload.get("k") or payload.get("data", {}).get("k")
                        if not k:
                            continue
                        candle = Candle(
                            symbol=self.normalize_symbol(symbol),
                            timeframe=timeframe,
                            open_time=datetime.fromtimestamp(k["t"] / 1000, tz=timezone.utc),
                            open=float(k["o"]),
                            high=float(k["h"]),
                            low=float(k["l"]),
                            close=float(k["c"]),
                            volume=float(k["v"]),
                            close_time=datetime.fromtimestamp(k["T"] / 1000, tz=timezone.utc),
                            quote_volume=float(k.get("q", 0) or 0),
                            trades=int(k.get("n", 0) or 0),
                        )
                        if handler is not None:
                            result = handler(candle)
                            if asyncio.iscoroutine(result):
                                await result
                        # Yield every update; consumers may filter on closed via close_time
                        yield candle
                        if k.get("x"):  # closed candle — keep yielding as above
                            pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — reconnect loop
                logger.warning(
                    "binance_ws_disconnected",
                    error=str(exc),
                    retry_in_s=backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(max_backoff, backoff * 2)

    @retry(
        retry=retry_if_exception_type(ExchangeUnavailableError),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        await self._limiter.acquire()
        try:
            resp = await self._client.request(method, path, params=params)
        except httpx.TransportError as exc:
            raise ExchangeUnavailableError(str(exc)) from exc

        if resp.status_code == 429:
            raise RateLimitError("Binance rate limit (HTTP 429)")
        if resp.status_code >= 500:
            raise ExchangeUnavailableError(f"Binance HTTP {resp.status_code}")
        if resp.status_code >= 400:
            raise ExchangeError(f"Binance HTTP {resp.status_code}: {resp.text}")
        return resp.json()
