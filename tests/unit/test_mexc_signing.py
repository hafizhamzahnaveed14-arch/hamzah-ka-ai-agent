"""MEXC signing unit tests (no network)."""

from alphaquant_data.adapters.mexc_signing import json_body_string, sign_mexc
from alphaquant_data.adapters.mexc_private import coins_to_contract_vol


def test_sign_stable():
    sig = sign_mexc(
        access_key="ak",
        secret_key="sk",
        timestamp_ms="1710000000000",
        param_string='{"symbol":"ETH_USDT"}',
    )
    assert len(sig) == 64
    assert sig == sign_mexc(
        access_key="ak",
        secret_key="sk",
        timestamp_ms="1710000000000",
        param_string='{"symbol":"ETH_USDT"}',
    )


def test_json_body_omits_nulls():
    s = json_body_string({"a": 1, "b": None, "c": "x"})
    assert "b" not in s
    assert '"a":1' in s


def test_coins_to_vol():
    assert coins_to_contract_vol(0.05, 0.01) == 5.0
