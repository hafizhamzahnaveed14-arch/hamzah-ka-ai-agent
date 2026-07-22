"""Live trading routes — human confirm required. Autopilot OFF."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from alphaquant_services.execution import LiveExecutionService, build_live_idea_from_evaluate
from alphaquant_shared.config import get_settings
from alphaquant_shared.errors import ConfigurationError, RiskViolationError
from alphaquant_shared.types import Side

router = APIRouter()


class LivePreviewRequest(BaseModel):
    symbol: str
    side: Side
    entry: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    account_equity: float = Field(gt=0)
    confluence_labels: list[str] = Field(default_factory=list)
    timeframes: list[dict[str, str]] = Field(
        default_factory=lambda: [
            {"timeframe": "1d", "bias": "bullish"},
            {"timeframe": "4h", "bias": "bullish"},
            {"timeframe": "1h", "bias": "bullish"},
            {"timeframe": "15m", "bias": "bullish"},
        ]
    )


class LiveConfirmRequest(BaseModel):
    confirm_token: str
    typed_yes: str = Field(description="Must be exactly YES")


@router.get("/live/status")
async def live_status():
    s = get_settings()
    armed = s.trading_mode == "live" and s.live_trading_enabled
    return {
        "trading_mode": s.trading_mode,
        "live_trading_enabled": s.live_trading_enabled,
        "armed": armed,
        "autopilot": False,
        "margin_mode": s.margin_mode,
        "target_leverage": s.target_leverage,
        "risk_per_trade_pct": s.risk_per_trade_pct,
        "note": (
            "Real orders require TRADING_MODE=live, LIVE_TRADING_ENABLED=true, "
            "preview → type YES → confirm. Autopilot is OFF."
            if not armed
            else "LIVE ARMED — human confirm still required per order. Money at risk."
        ),
    }


@router.post("/live/preview")
async def live_preview(body: LivePreviewRequest):
    """Build risk-checked idea + confirm token. Does not place an order."""
    try:
        tfs = [(t["timeframe"], t["bias"]) for t in body.timeframes]
        # Align timeframe biases with side
        if body.side == Side.SHORT:
            tfs = [(tf, "bearish") for tf, _ in tfs]
        else:
            tfs = [(tf, "bullish") for tf, _ in tfs]

        labels = body.confluence_labels or [
            "Break of Structure",
            "Order block reaction",
            "FVG / imbalance",
            "EMA alignment",
            "Volume confirmation",
            "Risk plan valid",
        ]
        idea = await build_live_idea_from_evaluate(
            symbol=body.symbol,
            side=body.side,
            entry=body.entry,
            stop_loss=body.stop_loss,
            account_equity=body.account_equity,
            confluence_labels=labels,
            timeframes=tfs,
        )
        if idea.action.value == "NO_TRADE":
            return {
                "ok": False,
                "idea": idea.model_dump(mode="json"),
                "reason": idea.no_trade_reason,
                "note": "NO TRADE — live order blocked by risk/confluence gates.",
            }

        svc = LiveExecutionService()
        preview = await svc.preview(idea=idea)
        return {
            "ok": True,
            "confirm_token": preview.confirm_token,
            "mexc_symbol": preview.mexc_symbol,
            "contract_vol": preview.contract_vol,
            "contract_size": preview.contract_size,
            "open_type": preview.open_type,
            "idea": preview.idea.model_dump(mode="json"),
            "disclaimer": preview.disclaimer,
        }
    except (ConfigurationError, RiskViolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/live/confirm")
async def live_confirm(body: LiveConfirmRequest):
    """Places a REAL MEXC order. Type YES required."""
    try:
        svc = LiveExecutionService()
        result = await svc.confirm(
            confirm_token=body.confirm_token,
            typed_yes=body.typed_yes,
        )
        return result
    except (ConfigurationError, RiskViolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
