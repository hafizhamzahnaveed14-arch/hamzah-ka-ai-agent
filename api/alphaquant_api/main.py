"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alphaquant_api.routes import health, live, market, signals
from alphaquant_shared.config import get_settings
from alphaquant_shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "api_starting",
        app=settings.app_name,
        trading_mode=settings.trading_mode,
        env=settings.app_env,
    )
    if settings.trading_mode == "live":
        if settings.live_trading_enabled:
            logger.warning(
                "live_armed",
                message=(
                    "LIVE TRADING ARMED. Human confirm still required per order. "
                    "Autopilot is OFF. Real money at risk — no guaranteed profits."
                ),
            )
        else:
            logger.warning(
                "live_mode_flag_set",
                message=(
                    "TRADING_MODE=live but LIVE_TRADING_ENABLED=false — "
                    "orders remain blocked until the second switch is enabled."
                ),
            )
    yield
    logger.info("api_stopping")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Crypto futures trading assistant. Proposes ideas with confidence "
            "scores and uncertainty — never guaranteed outcomes. "
            "NO TRADE is a valid and frequent result. Mode: "
            f"{settings.trading_mode.upper()}."
        ),
        lifespan=lifespan,
    )
    # Comma-separated production frontends, e.g. https://app.netlify.app,https://x.vercel.app
    extra = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    allow_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        *extra,
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(market.router, prefix="/api/v1", tags=["market"])
    app.include_router(signals.router, prefix="/api/v1", tags=["signals"])
    app.include_router(live.router, prefix="/api/v1", tags=["live"])
    return app


app = create_app()
