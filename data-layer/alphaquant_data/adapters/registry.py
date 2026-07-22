"""Adapter factory / registry. Default venue: MEXC Futures."""

from __future__ import annotations

from typing import Callable

from alphaquant_data.adapters.base import ExchangeAdapter
from alphaquant_data.adapters.binance_futures import BinanceFuturesAdapter
from alphaquant_data.adapters.mexc_futures import MexcFuturesAdapter
from alphaquant_data.adapters.stubs import (
    BybitAdapter,
    CoinbaseSpotAdapter,
    GateAdapter,
    OkxAdapter,
)
from alphaquant_shared.config import get_settings
from alphaquant_shared.errors import ConfigurationError

_REGISTRY: dict[str, Callable[[], ExchangeAdapter]] = {
    "mexc": MexcFuturesAdapter,
    "mexc_futures": MexcFuturesAdapter,
    "binance": BinanceFuturesAdapter,
    "binance_futures": BinanceFuturesAdapter,
    "bybit": BybitAdapter,
    "okx": OkxAdapter,
    "gate": GateAdapter,
    "gateio": GateAdapter,
    "coinbase": CoinbaseSpotAdapter,
}


def list_adapters() -> list[str]:
    return sorted(set(_REGISTRY.keys()))


def get_adapter(name: str | None = None) -> ExchangeAdapter:
    settings = get_settings()
    key = (name or settings.primary_exchange).lower().strip()
    factory = _REGISTRY.get(key)
    if factory is None:
        raise ConfigurationError(
            f"Unknown exchange '{name}'. Available: {', '.join(list_adapters())}"
        )
    return factory()
