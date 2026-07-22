"""MEXC private futures trading client (signed OPEN-API).

Places real orders only when explicitly called by LiveExecutionService.
Never used by the paper scanner.
"""

from __future__ import annotations

from typing import Any

import httpx

from alphaquant_data.adapters.mexc_signing import (
    json_body_string,
    mexc_timestamp_ms,
    query_param_string,
    sign_mexc,
)
from alphaquant_shared.config import Settings, get_settings
from alphaquant_shared.errors import ConfigurationError, ExchangeError
from alphaquant_shared.logging import get_logger
from alphaquant_shared.types import Side

logger = get_logger(__name__)


class MexcPrivateClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.mexc_api_key or not self.settings.mexc_api_secret:
            raise ConfigurationError(
                "MEXC_API_KEY and MEXC_API_SECRET required for live trading"
            )
        self._client = httpx.AsyncClient(
            base_url=self.settings.mexc_futures_rest.rstrip("/"),
            timeout=httpx.Timeout(30.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self, param_string: str) -> dict[str, str]:
        ts = mexc_timestamp_ms()
        sig = sign_mexc(
            access_key=self.settings.mexc_api_key,
            secret_key=self.settings.mexc_api_secret,
            timestamp_ms=ts,
            param_string=param_string,
        )
        return {
            "ApiKey": self.settings.mexc_api_key,
            "Request-Time": ts,
            "Signature": sig,
            "Content-Type": "application/json",
            "Recv-Window": "20",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        if method.upper() == "GET":
            param_string = query_param_string(params)
            headers = self._headers(param_string)
            resp = await self._client.get(path, params=params, headers=headers)
        else:
            body = json_body or {}
            param_string = json_body_string(body)
            headers = self._headers(param_string)
            # Send the exact JSON string that was signed
            resp = await self._client.request(
                method,
                path,
                content=param_string.encode("utf-8"),
                headers=headers,
            )

        if resp.status_code >= 400:
            raise ExchangeError(f"MEXC private HTTP {resp.status_code}: {resp.text}")
        payload = resp.json()
        if isinstance(payload, dict) and payload.get("success") is False:
            raise ExchangeError(f"MEXC private error: {payload}")
        return payload

    async def get_account_assets(self) -> Any:
        return await self._request("GET", "/api/v1/private/account/assets")

    async def get_open_positions(self, symbol: str | None = None) -> Any:
        path = "/api/v1/private/position/open_positions"
        params = {"symbol": symbol} if symbol else None
        return await self._request("GET", path, params=params)

    async def get_contract_detail(self, symbol: str) -> dict[str, Any]:
        # Public detail endpoint (no auth) — still via same client base
        resp = await self._client.get(f"/api/v1/contract/detail", params={"symbol": symbol})
        payload = resp.json()
        data = payload.get("data")
        if isinstance(data, list):
            row = next((d for d in data if d.get("symbol") == symbol), None)
            if not row:
                raise ExchangeError(f"Contract detail not found for {symbol}")
            return row
        if isinstance(data, dict):
            return data
        raise ExchangeError(f"Unexpected contract detail: {payload}")

    async def place_order(
        self,
        *,
        symbol: str,
        side: Side,
        price: float,
        vol: float,
        leverage: int,
        open_type: int,  # 1 isolated, 2 cross
        order_type: int = 5,  # 5 = market
        stop_loss: float | None = None,
        take_profit: float | None = None,
        external_oid: str | None = None,
    ) -> dict[str, Any]:
        """Place futures order. side LONG→1 open long, SHORT→3 open short."""
        mexc_side = 1 if side == Side.LONG else 3
        body: dict[str, Any] = {
            "symbol": symbol,
            "price": float(price),
            "vol": float(vol),
            "leverage": int(leverage),
            "side": mexc_side,
            "type": int(order_type),
            "openType": int(open_type),
        }
        if stop_loss is not None:
            body["stopLossPrice"] = float(stop_loss)
        if take_profit is not None:
            body["takeProfitPrice"] = float(take_profit)
        if external_oid:
            body["externalOid"] = external_oid

        logger.info(
            "mexc_place_order",
            symbol=symbol,
            side=side.value,
            vol=vol,
            leverage=leverage,
            open_type=open_type,
            order_type=order_type,
        )
        return await self._request("POST", "/api/v1/private/order/create", json_body=body)

    async def cancel_order(self, *, order_ids: list[str]) -> Any:
        return await self._request(
            "POST",
            "/api/v1/private/order/cancel",
            json_body={"orderIds": order_ids},
        )


def coins_to_contract_vol(coin_qty: float, contract_size: float) -> float:
    """Convert base-asset size to MEXC contract volume."""
    if contract_size <= 0:
        raise ExchangeError("Invalid contract_size")
    vol = coin_qty / contract_size
    # Floor to sane precision — venues reject tiny dust
    return max(round(vol, 4), 0.0)
