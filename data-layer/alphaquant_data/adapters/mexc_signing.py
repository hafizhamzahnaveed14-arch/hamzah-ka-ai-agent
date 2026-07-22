"""MEXC Futures HMAC signing (OPEN-API)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any


def mexc_timestamp_ms() -> str:
    return str(int(time.time() * 1000))


def sign_mexc(
    *,
    access_key: str,
    secret_key: str,
    timestamp_ms: str,
    param_string: str,
) -> str:
    """Signature = HMAC_SHA256(accessKey + timestamp + paramString)."""
    target = f"{access_key}{timestamp_ms}{param_string}"
    return hmac.new(
        secret_key.encode("utf-8"),
        target.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def json_body_string(payload: dict[str, Any]) -> str:
    """POST body for signing — compact JSON, nulls omitted."""
    cleaned = {k: v for k, v in payload.items() if v is not None}
    return json.dumps(cleaned, separators=(",", ":"), ensure_ascii=False)


def query_param_string(params: dict[str, Any] | None) -> str:
    """GET params: dictionary-sorted key=value&..."""
    if not params:
        return ""
    items = []
    for key in sorted(params.keys()):
        val = params[key]
        if val is None:
            continue
        items.append(f"{key}={val}")
    return "&".join(items)
