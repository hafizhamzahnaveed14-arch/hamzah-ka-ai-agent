"""Telegram / Discord notifications when secrets are configured."""

from __future__ import annotations

import httpx

from alphaquant_shared.config import get_settings
from alphaquant_shared.logging import get_logger
from alphaquant_shared.types import TradeIdea, format_trade_idea

logger = get_logger(__name__)


async def notify_signal(idea: TradeIdea, *, telegram: bool = False, discord: bool = False) -> None:
    text = format_trade_idea(idea)
    header = f"[PAPQuant · {idea.trading_mode.value.upper()}]\n"
    body = header + text
    settings = get_settings()

    logger.info(
        "signal_notification",
        symbol=idea.symbol,
        action=idea.action.value,
        telegram=telegram,
        discord=discord,
        preview=text[:240],
    )

    if telegram and settings.telegram_bot_token and settings.telegram_chat_id:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    url,
                    json={"chat_id": settings.telegram_chat_id, "text": body[:3900]},
                )
                if resp.status_code >= 400:
                    logger.warning("telegram_failed", status=resp.status_code, body=resp.text[:200])
        except Exception as exc:  # noqa: BLE001
            logger.warning("telegram_error", error=str(exc))

    if discord and settings.discord_webhook_url:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    settings.discord_webhook_url,
                    json={"content": body[:1900]},
                )
                if resp.status_code >= 400:
                    logger.warning("discord_failed", status=resp.status_code, body=resp.text[:200])
        except Exception as exc:  # noqa: BLE001
            logger.warning("discord_error", error=str(exc))
