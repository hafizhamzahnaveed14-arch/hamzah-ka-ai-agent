#!/usr/bin/env python3
"""Check whether the cloud API is armed for human-confirm live trading.

Usage:
  python scripts/check_live_ready.py
  python scripts/check_live_ready.py https://hamzah-ka-ai-agent-production.up.railway.app
"""

from __future__ import annotations

import json
import sys
import urllib.request

DEFAULT = "https://hamzah-ka-ai-agent-production.up.railway.app"


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT).rstrip("/")
    url = f"{base}/api/v1/live/status"
    print(f"GET {url}")
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 1

    print(json.dumps(data, indent=2))
    armed = bool(data.get("armed"))
    keys = bool(data.get("mexc_keys_configured"))
    print("---")
    print(f"armed={armed} mexc_keys_configured={keys} autopilot={data.get('autopilot')}")
    print(f"egress_ip={data.get('egress_ip')}")
    print(f"kill_switch={data.get('kill_switch')}")
    if armed and keys:
        print("READY: Preview → type YES → Confirm on the desk (small equity).")
        return 0
    print("NOT READY: set Railway API env per docs/REAL_TRADING.md then redeploy.")
    for item in data.get("missing") or []:
        print(f"  - {item}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
