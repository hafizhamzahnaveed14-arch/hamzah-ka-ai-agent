"""MEXC USDT-M Futures adapter (primary venue for this deployment)."""

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

# MEXC contract intervals (no native 3m — map to Min1 and note in docs)
_TF_TO_MEXC: dict[Timeframe, str] = {
    Timeframe.M1: "Min1",
    Timeframe.M3: "Min1",  # closest supported; consumers should prefer 1m/5m
    Timeframe.M5: "Min5",
    Timeframe.M15: "Min15",
    Timeframe.M30: "Min30",
    Timeframe.H1: "Min60",
    Timeframe.H4: "Hour4",
    Timeframe.D1: "Day1",
    Timeframe.W1: "Week1",
}


class MexcFuturesAdapter(ExchangeAdapter):
    """REST + websocket access to MEXC USD-M Futures contracts."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._owns_client = client is None
        base = self.settings.mexc_futures_rest.rstrip("/")
        self._client = client or httpx.AsyncClient(
            base_url=base,
            timeout=httpx.Timeout(30.0),
        )
        self._limiter = RateLimiter(requests_per_minute=300)
        self._closed = False

    @property
    def capabilities(self) -> ExchangeCapabilities:
        return ExchangeCapabilities(
            name="mexc_futures",
            supports_futures=True,
            supports_spot=False,
            supports_websocket=True,
            max_requests_per_minute=300,
        )

    def normalize_symbol(self, symbol: str) -> str:
        """ETHUSDT / XAUUSD / ETH_USDT → MEXC contract form (ETH_USDT, XAU_USDT)."""
        from alphaquant_shared.types import SYMBOL_ALIASES

        raw = symbol.upper().replace("-", "_").replace("/", "_").strip()
        compact = raw.replace("_", "")
        if raw in SYMBOL_ALIASES:
            compact = SYMBOL_ALIASES[raw]
        elif compact in SYMBOL_ALIASES:
            compact = SYMBOL_ALIASES[compact]
        return self._insert_quote_underscore(compact)

    def _insert_quote_underscore(self, compact: str) -> str:
        for quote in ("USDT", "USDC", "USD"):
            if compact.endswith(quote) and len(compact) > len(quote):
                return f"{compact[: -len(quote)]}_{quote}"
        return compact

    def to_internal_symbol(self, mexc_symbol: str) -> str:
        return mexc_symbol.replace("_", "")

    async def close(self) -> None:
        self._closed = True
        if self._owns_client:
            await self._client.aclose()

    async def ping(self) -> bool:
        try:
            await self._limiter.acquire()
            resp = await self._client.get("/api/v1/contract/ping")
            if resp.status_code != 200:
                return False
            data = resp.json()
            return bool(data.get("success", True))
        except Exception as exc:  # noqa: BLE001
            logger.warning("mexc_ping_failed", error=str(exc))
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
        interval = _TF_TO_MEXC[timeframe]
        params: dict[str, Any] = {"interval": interval}
        if start_time is not None:
            params["start"] = int(start_time.timestamp())
        if end_time is not None:
            params["end"] = int(end_time.timestamp())

        payload = await self._request_json("GET", f"/api/v1/contract/kline/{sym}", params=params)
        data = payload.get("data") or {}
        times = data.get("time") or []
        opens = data.get("open") or []
        highs = data.get("high") or []
        lows = data.get("low") or []
        closes = data.get("close") or []
        vols = data.get("vol") or []
        amounts = data.get("amount") or [None] * len(times)

        internal = self.to_internal_symbol(sym)
        candles: list[Candle] = []
        for i in range(len(times)):
            ts = int(times[i])
            # MEXC returns unix seconds
            open_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            candles.append(
                Candle(
                    symbol=internal,
                    timeframe=timeframe,
                    open_time=open_time,
                    open=float(opens[i]),
                    high=float(highs[i]),
                    low=float(lows[i]),
                    close=float(closes[i]),
                    volume=float(vols[i]),
                    quote_volume=float(amounts[i]) if amounts[i] is not None else None,
                )
            )
        if limit and len(candles) > limit:
            candles = candles[-limit:]
        return candles

    async def get_ticker_price(self, symbol: str) -> float:
        sym = self.normalize_symbol(symbol)
        payload = await self._request_json("GET", f"/api/v1/contract/ticker", params={"symbol": sym})
        data = payload.get("data")
        if isinstance(data, list):
            row = next((r for r in data if r.get("symbol") == sym), data[0] if data else None)
        else:
            row = data
        if not row:
            raise ExchangeError(f"MEXC ticker empty for {sym}")
        # lastPrice / fairPrice / lastPrice depending on endpoint version
        for key in ("lastPrice", "fairPrice", "indexPrice"):
            if key in row and row[key] is not None:
                return float(row[key])
        if "ask1" in row:
            return float(row["ask1"])
        raise ExchangeError(f"MEXC ticker missing price fields for {sym}: {row}")

    async def get_funding_rate(self, symbol: str) -> float | None:
        sym = self.normalize_symbol(symbol)
        payload = await self._request_json("GET", f"/api/v1/contract/funding_rate/{sym}")
        data = payload.get("data")
        if data is None:
            return None
        if isinstance(data, list) and data:
            data = data[0]
        rate = data.get("fundingRate") if isinstance(data, dict) else None
        return float(rate) if rate is not None else None

    async def get_open_interest(self, symbol: str) -> float | None:
        sym = self.normalize_symbol(symbol)
        # open interest often on ticker / open_interest endpoint
        try:
            payload = await self._request_json(
                "GET", f"/api/v1/contract/open_interest/{sym}"
            )
        except ExchangeError:
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        oi = data.get("openInterest") or data.get("amount")
        return float(oi) if oi is not None else None

    async def subscribe_klines(
        self,
        symbol: str,
        timeframe: Timeframe,
        handler: CandleHandler | None = None,
    ) -> AsyncIterator[Candle]:
        """MEXC contract websocket kline stream with reconnect/backoff."""
        sym = self.normalize_symbol(symbol)
        interval = _TF_TO_MEXC[timeframe]
        url = self.settings.mexc_futures_ws
        backoff = 1.0
        max_backoff = 60.0
        internal = self.to_internal_symbol(sym)

        while not self._closed:
            try:
                logger.info("mexc_ws_connecting", symbol=sym, interval=interval)
                async with websockets.connect(url, ping_interval=15, ping_timeout=20) as ws:
                    sub = {
                        "method": "sub.kline",
                        "param": {"symbol": sym, "interval": interval},
                    }
                    await ws.send(json.dumps(sub))
                    backoff = 1.0
                    async for raw in ws:
                        payload = json.loads(raw)
                        data = payload.get("data") or payload.get("d") or {}
                        if not isinstance(data, dict):
                            continue
                        # Common fields: o/h/l/c/q/t or open/high/low/close
                        o = data.get("open", data.get("o"))
                        h = data.get("high", data.get("h"))
                        l = data.get("low", data.get("l"))
                        c = data.get("close", data.get("c"))
                        v = data.get("vol", data.get("q", data.get("v", 0)))
                        t = data.get("t", data.get("time", data.get("windowStart")))
                        if o is None or c is None or t is None:
                            continue
                        ts = int(t)
                        if ts > 10_000_000_000:
                            ts = ts // 1000
                        candle = Candle(
                            symbol=internal,
                            timeframe=timeframe,
                            open_time=datetime.fromtimestamp(ts, tz=timezone.utc),
                            open=float(o),
                            high=float(h),
                            low=float(l),
                            close=float(c),
                            volume=float(v or 0),
                        )
                        if handler is not None:
                            result = handler(candle)
                            if asyncio.iscoroutine(result):
                                await result
                        yield candle
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("mexc_ws_disconnected", error=str(exc), retry_in_s=backoff)
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
            raise RateLimitError("MEXC rate limit (HTTP 429)")
        if resp.status_code >= 500:
            raise ExchangeUnavailableError(f"MEXC HTTP {resp.status_code}")
        if resp.status_code >= 400:
            raise ExchangeError(f"MEXC HTTP {resp.status_code}: {resp.text}")

        payload = resp.json()
        if isinstance(payload, dict) and payload.get("success") is False:
            raise ExchangeError(f"MEXC API error: {payload}")
        return payload
