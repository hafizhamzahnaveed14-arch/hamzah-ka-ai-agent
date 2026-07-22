"""Health, mode, and symbol universe endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from alphaquant_shared.config import get_settings
from alphaquant_shared.types import (
    ACTIVE_SYMBOLS,
    EXTRA_SYMBOLS,
    PHASE1_SYMBOLS,
    PHASE2_SYMBOLS,
    SYMBOL_ALIASES,
)

router = APIRouter()


@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "trading_mode": settings.trading_mode,
        "disclaimer": (
            "Signals carry uncertainty. No outcome is guaranteed. "
            "NO TRADE is a correct and frequent result."
        ),
    }


@router.get("/api/v1/mode")
async def trading_mode():
    settings = get_settings()
    return {
        "mode": settings.trading_mode,
        "label": "PAPER TRADING" if settings.trading_mode == "paper" else "LIVE",
        "live_execution_enabled": False,
        "note": "Live execution is gated behind paper-trading validation (Section 15).",
    }


@router.get("/api/v1/symbols")
async def symbols(universe: str = Query("active", pattern="^(phase1|phase2|active|all)$")):
    """Return tradable symbol lists. Gold is XAUUSDT (MEXC XAU_USDT)."""
    mapping = {
        "phase1": list(PHASE1_SYMBOLS),
        "phase2": list(PHASE2_SYMBOLS),
        "active": list(ACTIVE_SYMBOLS),
        "all": list(ACTIVE_SYMBOLS),
    }
    selected = mapping[universe]
    return {
        "universe": universe,
        "phase": 1 if universe == "phase1" else 2,
        "symbols": selected,
        "labels": {
            "XAUUSDT": "Gold (XAU)",
            "BTCUSDT": "Bitcoin",
            "ETHUSDT": "Ethereum",
            "DOGEUSDT": "Dogecoin",
            "SOLUSDT": "Solana",
        },
        "aliases": SYMBOL_ALIASES,
        "groups": {
            "phase1": list(PHASE1_SYMBOLS),
            "phase2": list(PHASE2_SYMBOLS),
            "extra": list(EXTRA_SYMBOLS),
        },
        "note": "No symbol is guaranteed to be profitable. Scan quality varies by regime.",
    }
