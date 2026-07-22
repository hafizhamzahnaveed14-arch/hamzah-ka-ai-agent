"""Abstract exchange adapter — strategies must not import concrete venues."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from alphaquant_shared.types import Candle, Timeframe


@dataclass(frozen=True)
class ExchangeCapabilities:
    name: str
    supports_futures: bool
    supports_spot: bool
    supports_websocket: bool
    max_requests_per_minute: int


CandleHandler = Callable[[Candle], Awaitable[None] | None]


class ExchangeAdapter(ABC):
    """Common interface for all venues.

    Implementations must:
    - Respect rate limits and surface RateLimitError
    - Reconnect websockets with exponential backoff
    - Never assume continuous uptime
    """

    @property
    @abstractmethod
    def capabilities(self) -> ExchangeCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def ping(self) -> bool:
        """Return True if the venue is reachable."""

    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        limit: int = 500,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    async def get_ticker_price(self, symbol: str) -> float:
        raise NotImplementedError

    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> float | None:
        """Perpetual funding rate, or None if not applicable."""

    @abstractmethod
    async def get_open_interest(self, symbol: str) -> float | None:
        raise NotImplementedError

    @abstractmethod
    def subscribe_klines(
        self,
        symbol: str,
        timeframe: Timeframe,
        handler: CandleHandler | None = None,
    ) -> AsyncIterator[Candle]:
        """Async iterator yielding candles; reconnect on disconnect."""
        raise NotImplementedError

    async def close(self) -> None:
        """Release HTTP/WS resources."""

    def normalize_symbol(self, symbol: str) -> str:
        return symbol.upper().replace("/", "").replace("-", "")

    async def health(self) -> dict[str, Any]:
        ok = await self.ping()
        return {
            "exchange": self.capabilities.name,
            "ok": ok,
            "supports_futures": self.capabilities.supports_futures,
        }
