"""Live trading routes — human confirm required. Autopilot OFF."""

from __future__ import annotations

import httpx
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


async def _egress_ip() -> str | None:
    """Outbound IP Railway uses — whitelist this on MEXC."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://api.ipify.org")
            resp.raise_for_status()
            return resp.text.strip() or None
    except Exception:  # noqa: BLE001 — status must still return
        return None


@router.get("/live/egress")
async def live_egress():
    ip = await _egress_ip()
    return {
        "egress_ip": ip,
        "note": (
            "Add this IP to your MEXC API key whitelist. "
            "If null, open Railway API shell and run: curl -s https://api.ipify.org"
        ),
    }


@router.get("/live/status")
async def live_status():
    s = get_settings()
    keys_ok = bool(s.mexc_api_key and s.mexc_api_secret)
    armed = s.trading_mode == "live" and s.live_trading_enabled
    egress = await _egress_ip()
    missing: list[str] = []
    if s.trading_mode != "live":
        missing.append("Set TRADING_MODE=live on Railway API")
    if not s.live_trading_enabled:
        missing.append("Set LIVE_TRADING_ENABLED=true on Railway API")
    if not keys_ok:
        missing.append("Set MEXC_API_KEY and MEXC_API_SECRET on Railway API")
    if egress:
        missing.append(f"Whitelist MEXC API IP: {egress}")
    else:
        missing.append("Could not detect egress IP — check /api/v1/live/egress")

    # Whitelist is external; don't block "ready_except_ip" messaging
    checklist = {
        "trading_mode_live": s.trading_mode == "live",
        "live_trading_enabled": s.live_trading_enabled,
        "mexc_keys_configured": keys_ok,
        "egress_ip": egress,
        "cors_origins_set": bool(s.cors_origins.strip()),
        "autopilot": False,
    }
    return {
        "trading_mode": s.trading_mode,
        "live_trading_enabled": s.live_trading_enabled,
        "armed": armed,
        "mexc_keys_configured": keys_ok,
        "ready_for_preview": armed and keys_ok,
        "autopilot": False,
        "margin_mode": s.margin_mode,
        "target_leverage": s.target_leverage,
        "risk_per_trade_pct": s.risk_per_trade_pct,
        "egress_ip": egress,
        "checklist": checklist,
        "missing": missing if not (armed and keys_ok) else (
            [f"Whitelist MEXC API IP: {egress}"] if egress else []
        ),
        "kill_switch": "Set LIVE_TRADING_ENABLED=false on Railway API and redeploy.",
        "existing_positions_note": (
            "Manual MEXC positions (CROSS) share margin with any new desk order. "
            "If you already hold multiple 200x positions on a small wallet, "
            "do not add size until equity/available margin recovers."
        ),
        "note": (
            "Real orders require TRADING_MODE=live, LIVE_TRADING_ENABLED=true, "
            "MEXC keys, IP whitelist, preview → type YES → confirm. Autopilot is OFF."
            if not armed
            else (
                "LIVE ARMED — human confirm still required per order. Money at risk. "
                + (f"Whitelist IP {egress} on MEXC if not done." if egress else "")
            )
        ),
    }


@router.get("/live/account")
async def live_account():
    """Read-only MEXC wallet + open positions (requires API keys)."""
    s = get_settings()
    if not (s.mexc_api_key and s.mexc_api_secret):
        raise HTTPException(
            status_code=400,
            detail="Set MEXC_API_KEY and MEXC_API_SECRET on Railway API first",
        )
    from alphaquant_data.adapters.mexc_private import MexcPrivateClient

    client = MexcPrivateClient(s)
    try:
        assets = await client.get_account_assets()
        positions = await client.get_open_positions()
        pos_data = positions.get("data") if isinstance(positions, dict) else positions
        if not isinstance(pos_data, list):
            pos_data = []
        asset_data = assets.get("data") if isinstance(assets, dict) else assets
        return {
            "ok": True,
            "assets": asset_data,
            "open_positions": pos_data,
            "open_position_count": len(pos_data),
            "suggested_desk_equity_usdt": _suggest_equity(asset_data),
            "warning": (
                "CROSS positions share one wallet. Adding another 200x order "
                "increases liquidation risk for ALL open positions."
                if pos_data
                else None
            ),
            "note": "Read-only. Desk Confirm still required to place new orders.",
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await client.close()


def _suggest_equity(asset_data: object) -> float | None:
    """Best-effort USDT equity from MEXC assets payload."""
    rows: list = []
    if isinstance(asset_data, list):
        rows = asset_data
    elif isinstance(asset_data, dict):
        inner = asset_data.get("assets") or asset_data.get("data") or []
        if isinstance(inner, list):
            rows = inner
    for row in rows:
        if not isinstance(row, dict):
            continue
        currency = str(row.get("currency") or row.get("symbol") or "").upper()
        if currency in {"USDT", "USDC"}:
            for key in ("equity", "availableBalance", "available", "cashBalance", "balance"):
                val = row.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        continue
    return None


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
