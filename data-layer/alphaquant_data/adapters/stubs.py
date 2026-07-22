"""Stub adapters for Phase-2 venues — interface-ready, not fully implemented."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from alphaquant_data.adapters.base import CandleHandler, ExchangeAdapter, ExchangeCapabilities
from alphaquant_shared.errors import ExchangeError
from alphaquant_shared.types import Candle, Timeframe


class _UnimplementedFuturesAdapter(ExchangeAdapter):
    """Placeholder so registry can list planned venues without breaking imports."""

    venue_name: str = "unimplemented"

    @property
    def capabilities(self) -> ExchangeCapabilities:
        return ExchangeCapabilities(
            name=self.venue_name,
            supports_futures=True,
            supports_spot=False,
            supports_websocket=True,
            max_requests_per_minute=100,
        )

    async def ping(self) -> bool:
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
        raise ExchangeError(f"{self.venue_name} adapter not implemented yet")

    async def get_ticker_price(self, symbol: str) -> float:
        raise ExchangeError(f"{self.venue_name} adapter not implemented yet")

    async def get_funding_rate(self, symbol: str) -> float | None:
        raise ExchangeError(f"{self.venue_name} adapter not implemented yet")

    async def get_open_interest(self, symbol: str) -> float | None:
        raise ExchangeError(f"{self.venue_name} adapter not implemented yet")

    async def subscribe_klines(
        self,
        symbol: str,
        timeframe: Timeframe,
        handler: CandleHandler | None = None,
    ) -> AsyncIterator[Candle]:
        raise ExchangeError(f"{self.venue_name} adapter not implemented yet")
        yield  # pragma: no cover


class BybitAdapter(_UnimplementedFuturesAdapter):
    venue_name = "bybit"


class OkxAdapter(_UnimplementedFuturesAdapter):
    venue_name = "okx"


class MexcAdapter:
    """Deprecated stub — use MexcFuturesAdapter via registry ``mexc``."""

    def __init__(self) -> None:
        from alphaquant_data.adapters.mexc_futures import MexcFuturesAdapter

        raise RuntimeError(
            "Use get_adapter('mexc') / MexcFuturesAdapter — stub removed"
        )


class GateAdapter(_UnimplementedFuturesAdapter):
    venue_name = "gateio"


class CoinbaseSpotAdapter(_UnimplementedFuturesAdapter):
    venue_name = "coinbase_spot"

    @property
    def capabilities(self) -> ExchangeCapabilities:
        return ExchangeCapabilities(
            name=self.venue_name,
            supports_futures=False,
            supports_spot=True,
            supports_websocket=True,
            max_requests_per_minute=100,
        )
