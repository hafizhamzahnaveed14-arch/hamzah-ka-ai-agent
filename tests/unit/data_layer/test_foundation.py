"""Shared types and adapter registry tests."""

from __future__ import annotations

import pytest

from alphaquant_data.adapters.registry import get_adapter, list_adapters
from alphaquant_data.adapters.rate_limit import RateLimiter
from alphaquant_shared.config import Settings
from alphaquant_shared.types import PHASE1_SYMBOLS, SignalAction, TradeIdea, format_trade_idea


def test_phase1_symbols():
    assert "ETHUSDT" in PHASE1_SYMBOLS
    assert "BTCUSDT" not in PHASE1_SYMBOLS


def test_settings_risk_cap_half_percent():
    s = Settings(risk_per_trade_pct=0.005, risk_per_trade_hard_cap_pct=0.005)
    assert s.effective_risk_per_trade_pct(0.01) == 0.005
    assert s.primary_exchange == "mexc"


def test_no_trade_format():
    idea = TradeIdea(
        symbol="ADAUSDT",
        action=SignalAction.NO_TRADE,
        no_trade_reason="1H and 4H trend disagree",
    )
    text = format_trade_idea(idea)
    assert text.startswith("ADAUSDT — NO TRADE")
    assert "disagree" in text


def test_adapter_registry_default_mexc():
    assert "mexc" in list_adapters()
    adapter = get_adapter("mexc")
    assert adapter.capabilities.name == "mexc_futures"
    assert adapter.normalize_symbol("ETHUSDT") == "ETH_USDT"
    assert adapter.normalize_symbol("XAUUSD") == "XAU_USDT"
    assert adapter.normalize_symbol("XAUUSDT") == "XAU_USDT"
    assert adapter.normalize_symbol("DOGEUSDT") == "DOGE_USDT"


@pytest.mark.asyncio
async def test_rate_limiter_allows_burst_within_budget():
    limiter = RateLimiter(requests_per_minute=60, max_wait_s=1)
    await limiter.acquire()
    await limiter.acquire()
