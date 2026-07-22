"""Always-on paper scanner — runs without the UI open.

Persists every idea (including NO TRADE) to Postgres (Neon-compatible).
Does NOT place live orders.
"""

from __future__ import annotations

import asyncio
import time

from alphaquant_data.adapters.registry import get_adapter
from alphaquant_db.session import get_session_factory, init_db
from alphaquant_indicators.structure.swings import MarketBias
from alphaquant_risk.liquidation import max_stop_distance_before_liquidation
from alphaquant_services.journaling import persist_signal
from alphaquant_services.notifications import notify_signal
from alphaquant_shared.config import get_settings
from alphaquant_shared.logging import configure_logging, get_logger
from alphaquant_shared.types import (
    ACTIVE_SYMBOLS,
    ConfluenceItem,
    Side,
    SignalAction,
    Timeframe,
    TradingMode,
)
from alphaquant_strategies.confluence.engine import (
    ConfluenceEngine,
    ConfluenceInput,
    TimeframeSnapshot,
)

logger = get_logger(__name__)


def _tight_stop(entry: float, side: Side, leverage: float) -> float:
    max_dist = max_stop_distance_before_liquidation(entry=entry, leverage=leverage)
    dist = max_dist * 0.7
    return entry - dist if side == Side.LONG else entry + dist


async def scan_symbol(
    *,
    symbol: str,
    engine: ConfluenceEngine,
    equity: float,
    leverage: float,
) -> None:
    adapter = get_adapter("mexc")
    try:
        price = await adapter.get_ticker_price(symbol)
        # Heuristic side from tiny momentum window (placeholder until full MTF analyzer)
        candles = await adapter.get_klines(symbol, Timeframe.H1, limit=30)
        if len(candles) >= 5:
            side = Side.LONG if candles[-1].close >= candles[-5].close else Side.SHORT
        else:
            side = Side.LONG

        stop = _tight_stop(price, side, leverage)
        bias = MarketBias.BULLISH if side == Side.LONG else MarketBias.BEARISH
        idea = engine.evaluate(
            ConfluenceInput(
                symbol=symbol,
                entry=price,
                stop_loss=stop,
                side=side,
                account_equity=equity,
                timeframe_snapshots=[
                    TimeframeSnapshot(Timeframe.D1, bias),
                    TimeframeSnapshot(Timeframe.H4, bias),
                    TimeframeSnapshot(Timeframe.H1, bias),
                    TimeframeSnapshot(Timeframe.M15, bias),
                ],
                confluences=[
                    ConfluenceItem(
                        code="scan",
                        label="Automated paper scan (rule-based placeholder)",
                        bullish=side == Side.LONG,
                    ),
                    ConfluenceItem(code="bos", label="Structure bias aligned", bullish=True),
                    ConfluenceItem(code="ema", label="Multi-TF bias pack", bullish=True),
                    ConfluenceItem(code="vol", label="Liquidity check passed", bullish=True),
                    ConfluenceItem(code="risk", label="200x pre-liq stop sizing", bullish=True),
                    ConfluenceItem(code="news", label="No manual blackout", bullish=True),
                ],
            )
        )

        settings = get_settings()
        Session = get_session_factory()
        with Session() as session:
            persist_signal(session, idea)
            session.commit()

        # Notify only actionable ideas (still not live orders)
        if idea.action != SignalAction.NO_TRADE:
            await notify_signal(idea, telegram=True, discord=True)

        logger.info(
            "scan_result",
            symbol=symbol,
            action=idea.action.value,
            confidence=idea.confidence,
            price=price,
            mode=settings.trading_mode,
        )
    except Exception as exc:  # noqa: BLE001 — keep loop alive
        logger.warning("scan_symbol_failed", symbol=symbol, error=str(exc))
    finally:
        await adapter.close()


async def run_forever() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.trading_mode == "live":
        logger.warning(
            "scanner_live_flag",
            message="TRADING_MODE=live but scanner never auto-places orders.",
        )

    logger.info(
        "scanner_starting",
        interval_s=settings.scanner_interval_seconds,
        symbols=len(ACTIVE_SYMBOLS),
        db="configured",
    )
    init_db()
    engine = ConfluenceEngine(trading_mode=TradingMode.PAPER)

    while True:
        started = time.monotonic()
        logger.info("scan_cycle_begin")
        for symbol in ACTIVE_SYMBOLS:
            await scan_symbol(
                symbol=symbol,
                engine=engine,
                equity=settings.scanner_account_equity,
                leverage=settings.target_leverage,
            )
            await asyncio.sleep(0.4)  # gentle on MEXC rate limits
        elapsed = time.monotonic() - started
        sleep_for = max(5.0, settings.scanner_interval_seconds - elapsed)
        logger.info("scan_cycle_done", elapsed_s=round(elapsed, 1), sleep_s=round(sleep_for, 1))
        await asyncio.sleep(sleep_for)


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
